import json, re, threading
from datetime import date, timedelta
from wsgiref.simple_server import make_server, WSGIRequestHandler
import pytest
from playwright.sync_api import sync_playwright, expect
from evtrack.models import Task
from evtrack.storage import JsonStore
from evtrack.web import make_web_app

TODAY = date.today()


class Q(WSGIRequestHandler):
    def log_message(self, *a): pass


@pytest.fixture
def site(tmp_path):
    s = JsonStore(tmp_path / "s.json")
    s.add(Task("Write report", priority=1, tags=["work"], due=TODAY + timedelta(days=2)))
    s.add(Task("Buy milk", tags=["home", "shop"], due=TODAY - timedelta(days=1)))
    s.add(Task("Old thing", status="done", priority=3))
    srv = make_server("127.0.0.1", 0, make_web_app(s), handler_class=Q)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{srv.server_port}/"); pg.wait_for_selector('[data-testid=task-row]')
        yield pg, s, errs
        b.close()
    srv.shutdown()


def rows(pg): return pg.locator('[data-testid=task-row]')


def test_initial_list(site):
    pg, s, errs = site
    expect(rows(pg)).to_have_count(3)
    ids = [rows(pg).nth(i).get_attribute("data-id") for i in range(3)]
    assert ids == ["1", "2", "3"]
    expect(pg.locator("#counter")).to_have_text("2 open · 1 done")
    r2 = pg.locator('[data-testid=task-row][data-id="2"]')
    assert "overdue" in r2.get_attribute("class").split()
    expect(r2.locator(".tag")).to_have_count(2)
    expect(r2.locator(".priority")).to_have_text("P2")
    expect(pg.locator('[data-id="1"] .due')).to_have_text((TODAY + timedelta(days=2)).isoformat())
    assert pg.locator('[data-id="3"] .toggle').is_checked()
    assert pg.locator("#empty").is_hidden()
    assert not errs


def test_add_and_error(site):
    pg, s, _ = site
    pg.fill("#quick-add", "Call Bob #phone !1"); pg.press("#quick-add", "Enter")
    expect(rows(pg)).to_have_count(4)
    expect(pg.locator("#quick-add")).to_have_value("")
    assert s.__class__(s.path).get(4).tags == ["phone"]
    pg.fill("#quick-add", "bad !9"); pg.press("#quick-add", "Enter")
    expect(pg.locator("#error")).to_be_visible()
    expect(pg.locator("#quick-add")).to_have_value("bad !9")
    pg.fill("#quick-add", "fine"); pg.press("#quick-add", "Enter")
    expect(pg.locator("#error")).to_be_hidden()


def test_toggle_delete(site):
    pg, s, _ = site
    pg.locator('[data-id="1"] .toggle').click()
    expect(pg.locator("#counter")).to_have_text("1 open · 2 done")
    assert JsonStore(s.path).get(1).status == "done"
    pg.get_by_label("Delete Buy milk").click()
    expect(rows(pg)).to_have_count(2)
    with pytest.raises(KeyError): JsonStore(s.path).get(2)


def test_filter_and_empty(site):
    pg, s, _ = site
    pg.fill("#filter", "tag:home"); expect(rows(pg)).to_have_count(1)
    pg.fill("#filter", "foo:bar"); expect(pg.locator("#error")).to_be_visible(); expect(rows(pg)).to_have_count(1)
    pg.fill("#filter", "nothingmatches"); expect(rows(pg)).to_have_count(0)
    expect(pg.locator("#empty")).to_be_visible()


def test_mobile_no_hscroll(site):
    pg, *_ = site
    pg.set_viewport_size({"width": 375, "height": 800}); pg.wait_for_timeout(200)
    assert pg.evaluate("document.documentElement.scrollWidth") <= 375
