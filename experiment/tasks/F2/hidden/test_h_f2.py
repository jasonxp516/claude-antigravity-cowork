import json, threading, tempfile
from datetime import date, timedelta
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler
import pytest
from playwright.sync_api import sync_playwright, expect
from evtrack.models import Task
from evtrack.storage import JsonStore
from evtrack.web import make_web_app

T = date.today(); D = lambda n: T + timedelta(days=n)


class Q(WSGIRequestHandler):
    def log_message(self, *a): pass


@pytest.fixture
def site(tmp_path):
    s = JsonStore(tmp_path / "s.json")
    s.add(Task("Write report", priority=1, tags=["work"], due=D(1)))
    s.add(Task("Buy milk", tags=["home"], due=D(-1)))
    s.add(Task("Gym", priority=3, tags=["rec-weekly", "health"], due=D(0)))
    s.add(Task("Old", status="done", priority=3))
    srv = make_server("127.0.0.1", 0, make_web_app(s), handler_class=Q)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}/"
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        yield pg, base, s, errs, tmp_path
        b.close()
    srv.shutdown()


def go(pg, base, h):
    pg.goto(base + h); pg.wait_for_timeout(300)


def test_nav_and_routing(site):
    pg, base, s, errs, _ = site
    go(pg, base, "")
    expect(pg.locator("#view")).to_have_attribute("data-view", "tasks")
    pg.click('nav a[href="#/stats"]')
    expect(pg.locator("#view")).to_have_attribute("data-view", "stats")
    expect(pg.locator('nav a[href="#/stats"]')).to_have_attribute("aria-current", "page")
    assert pg.locator('nav a[href="#/tasks"]').get_attribute("aria-current") != "page"
    go(pg, base, "#/nonsense"); expect(pg.locator("#view")).to_have_attribute("data-view", "tasks")
    pg.goto(base + "#/agenda"); pg.reload(); expect(pg.locator("#view")).to_have_attribute("data-view", "agenda")
    assert not errs


def test_tasks_view(site):
    pg, base, s, errs, _ = site
    go(pg, base, "#/tasks")
    rows = pg.locator("[data-testid=task-row]"); expect(rows).to_have_count(4)
    assert [rows.nth(i).get_attribute("data-id") for i in range(4)] == ["1", "2", "3", "4"]
    expect(pg.locator("#counter")).to_have_text("3 open · 1 done")
    assert "overdue" in pg.locator('[data-testid=task-row][data-id="2"]').get_attribute("class").split()
    pg.fill("#quick-add", "New one #x !2"); pg.press("#quick-add", "Enter"); expect(rows).to_have_count(5)
    pg.fill("#quick-add", "bad !9"); pg.press("#quick-add", "Enter"); expect(pg.locator("#error")).to_be_visible()
    pg.locator('[data-id="1"] .toggle').click(); expect(pg.locator("#counter")).to_have_text("3 open · 2 done")
    pg.get_by_label("Delete Buy milk").click(); expect(rows).to_have_count(4)
    pg.fill("#filter", "tag:health"); expect(rows).to_have_count(1)


def test_task_edit(site):
    pg, base, s, errs, _ = site
    go(pg, base, "#/tasks"); pg.locator('[data-id="1"] a.title').click()
    expect(pg.locator("#view")).to_have_attribute("data-view", "task")
    expect(pg.locator("[name=title]")).to_have_value("Write report")
    expect(pg.locator("[name=tags]")).to_have_value("work")
    pg.fill("[name=title]", "Write final report"); pg.fill("[name=tags]", "work, q4 ,")
    pg.select_option("[name=priority]", "2"); pg.fill("[name=due]", "")
    pg.locator("#edit-form [type=submit]").click()
    expect(pg.locator("#saved")).to_contain_text("Saved")
    t = JsonStore(s.path).get(1)
    assert (t.title, t.tags, t.priority, t.due) == ("Write final report", ["work", "q4"], 2, None)
    pg.fill("[name=title]", " "); pg.locator("#edit-form [type=submit]").click()
    expect(pg.locator("#error")).to_be_visible()
    pg.click("#delete-task"); expect(pg.locator("#view")).to_have_attribute("data-view", "tasks")
    with pytest.raises(KeyError): JsonStore(s.path).get(1)
    go(pg, base, "#/task/999"); expect(pg.locator("#error")).to_be_visible()


def test_agenda(site):
    pg, base, s, errs, _ = site
    go(pg, base, "#/agenda")
    days = pg.locator("[data-testid=agenda-day]"); expect(days).to_have_count(7)
    assert days.nth(0).get_attribute("data-date") == T.isoformat()
    first = days.nth(0).locator("[data-testid=agenda-item]")
    expect(first).to_have_count(2)   # Gym due today + overdue Buy milk on start day
    pg.click("#next-week"); expect(days.nth(0)).to_have_attribute("data-date", D(7).isoformat())
    assert D(7).isoformat() in pg.url
    pg.click("#prev-week"); expect(days.nth(0)).to_have_attribute("data-date", T.isoformat())
    pg.get_by_label("Complete Gym").click()
    expect(pg.locator("#notice")).to_be_visible()
    assert JsonStore(s.path).get(3).status == "done" and JsonStore(s.path).get(5).due == D(7)


def test_stats(site):
    pg, base, s, errs, _ = site
    go(pg, base, "#/stats")
    expect(pg.locator("[data-testid=stat-total]")).to_contain_text("4")
    expect(pg.locator("[data-testid=stat-open]")).to_contain_text("3")
    expect(pg.locator("[data-testid=stat-rate]")).to_contain_text("25.0%")
    expect(pg.locator("[data-testid=prio-bar]")).to_have_count(3)
    expect(pg.locator('[data-testid=prio-bar][data-p="1"]')).to_contain_text("1")
    expect(pg.locator("[data-testid=overdue-item]")).to_have_count(1)
    expect(pg.locator("[data-testid=tag-stat]").first).to_be_visible()


def test_io(site):
    pg, base, s, errs, tmp = site
    go(pg, base, "#/io")
    assert pg.locator("a#export-csv").get_attribute("href").endswith("/api/export.csv")
    assert pg.locator("a#export-ics").get_attribute("download") is not None
    f = tmp / "in.csv"; f.write_text("id,title,status,priority,tags,due\n1,Imported A,open,2,,\n2,Imported B,open,1,x,\n")
    pg.set_input_files("#import-file", str(f)); pg.click("#import-btn")
    expect(pg.locator("#import-result")).to_contain_text("Imported 2 tasks")
    assert len(JsonStore(s.path).list()) == 6
    g = tmp / "bad.csv"; g.write_text("nope\n")
    pg.set_input_files("#import-file", str(g)); pg.click("#import-btn")
    expect(pg.locator("#error")).to_be_visible()


def test_mobile_all_views(site):
    pg, base, *_ = site
    pg.set_viewport_size({"width": 375, "height": 800})
    for h in ["#/tasks", "#/task/1", "#/agenda", "#/stats", "#/io"]:
        go(pg, base, h)
        assert pg.evaluate("document.documentElement.scrollWidth") <= 375, h
