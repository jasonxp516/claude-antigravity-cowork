from datetime import date as D
from evtrack.models import Task
from evtrack.stats import compute_stats, format_stats
T = D(2026, 11, 10)


def mk():
    return [Task("a", id=1, tags=["Home"], due=D(2026, 11, 1)),
            Task("b", id=2, priority=1, tags=["work", "home"], due=D(2026, 11, 12)),
            Task("c", id=3, status="done", tags=["work"]),
            Task("d", id=4, priority=3, tags=["zz", "aa"], due=D(2026, 11, 16)),
            Task("e", id=5, due=D(2026, 11, 17)),
            Task("f", id=6, priority=1, due=D(2026, 10, 30))]


def test_compute():
    s = compute_stats(mk(), T)
    assert (s["total"], s["open"], s["done"], s["completion_rate"]) == (6, 5, 1, 0.167)
    assert s["by_priority"] == {1: 2, 2: 2, 3: 1}
    assert list(s["by_tag"].items()) == [("home", 2), ("aa", 1), ("work", 1), ("zz", 1)]
    assert s["overdue"] == [6, 1] and s["due_this_week"] == [2, 4] and s["oldest_open_id"] == 1


def test_empty():
    s = compute_stats([], T)
    assert s["completion_rate"] == 0.0 and s["by_priority"] == {1: 0, 2: 0, 3: 0} and s["oldest_open_id"] is None
    assert format_stats(s) == "Tasks: 0 (open 0, done 0, 0.0% complete)\nPriority: p1=0 p2=0 p3=0\nTags: -\nOverdue: none\nThis week: none"


def test_format():
    assert format_stats(compute_stats(mk(), T)) == (
        "Tasks: 6 (open 5, done 1, 16.7% complete)\nPriority: p1=2 p2=2 p3=1\n"
        "Tags: home(2), aa(1), work(1), zz(1)\nOverdue: 6, 1\nThis week: 2, 4")
