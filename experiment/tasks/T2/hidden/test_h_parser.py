from datetime import date
import pytest
from evtrack.parser import parse_quick, parse_to_task
T = date(2026, 11, 10)


def test_basic():
    r = parse_quick("Buy  milk #Home #home !1 due:tomorrow #x-y", T)
    assert r == {"title": "Buy milk", "tags": ["home", "x-y"], "priority": 1, "due": date(2026, 11, 11)}


def test_defaults_and_hash_words():
    r = parse_quick("fix # issue #? now", T)
    assert r["title"] == "fix # issue #? now" and r["tags"] == [] and r["priority"] == 2 and r["due"] is None


@pytest.mark.parametrize("tok,exp", [("due:today", date(2026, 11, 10)), ("due:+0d", date(2026, 11, 10)),
                                     ("due:+30d", date(2026, 12, 10)), ("due:2027-02-28", date(2027, 2, 28))])
def test_due(tok, exp):
    assert parse_quick(f"a {tok}", T)["due"] == exp


@pytest.mark.parametrize("s", ["a !4", "a !x", "a !1 !2", "a due:2027-02-30", "a due:soon", "a due:+d",
                               "a due:today due:tomorrow", "#only !1", "", "   "])
def test_errors(s):
    with pytest.raises(ValueError):
        parse_quick(s, T)


def test_to_task():
    t = parse_to_task("x #a !3", T)
    assert t.title == "x" and t.tags == ["a"] and t.priority == 3 and t.id is None
