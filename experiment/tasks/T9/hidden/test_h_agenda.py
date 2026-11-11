from datetime import date as D
import pytest
from evtrack.models import Task
from evtrack.storage import JsonStore
from evtrack.agenda import complete, agenda, render_agenda


def test_complete_recurring(tmp_path):
    s = JsonStore(tmp_path / "s.json")
    s.add(Task("pay rent", priority=1, tags=["home", "rec-monthly"], due=D(2026, 1, 31)))
    n = complete(s, 1, D(2026, 1, 20))
    assert s.get(1).status == "done" and n.id == 2 and n.due == D(2026, 2, 28) and n.status == "open"
    assert n.tags == ["home", "rec-monthly"] and n.priority == 1 and n.title == "pay rent"
    s.add(Task("water", tags=["rec-every:3d"], due=D(2026, 1, 1)))
    assert complete(s, 3, D(2026, 1, 10)).due == D(2026, 1, 10)


def test_complete_non_recurring_and_errors(tmp_path):
    s = JsonStore(tmp_path / "s.json")
    s.add(Task("a", due=D(2026, 1, 1))); s.add(Task("b", tags=["rec-daily"]))
    assert complete(s, 1, D(2026, 1, 1)) is None
    assert complete(s, 2, D(2026, 1, 1)) is None and len(s.list()) == 2
    with pytest.raises(ValueError): complete(s, 1, D(2026, 1, 1))
    s.add(Task("c", tags=["rec-daily", "rec-weekly"], due=D(2026, 1, 1)))
    with pytest.raises(ValueError): complete(s, 3, D(2026, 1, 1))


def test_agenda():
    ts = [Task("late", id=1, priority=3, due=D(2026, 11, 8)),
          Task("gym", id=2, priority=2, tags=["rec-every:2d"], due=D(2026, 11, 10)),
          Task("call", id=3, priority=1, due=D(2026, 11, 10)),
          Task("done", id=4, status="done", due=D(2026, 11, 10)),
          Task("far", id=5, due=D(2026, 12, 1))]
    a = agenda(ts, D(2026, 11, 10), days=4)
    assert [d for d, _ in a] == [D(2026, 11, 10), D(2026, 11, 11), D(2026, 11, 12), D(2026, 11, 13)]
    assert [t.id for t in a[0][1]] == [3, 2, 1]
    assert a[1][1] == [] and [t.id for t in a[2][1]] == [2] and a[3][1] == []
    with pytest.raises(ValueError): agenda(ts, D(2026, 11, 10), days=0)
    out = render_agenda(a)
    assert out == ("2026-11-10 Tue\n  - [p1] call\n  - [p2] gym\n  - [p3] late (overdue)\n\n"
                   "2026-11-11 Wed\n  (nothing)\n\n2026-11-12 Thu\n  - [p2] gym\n\n2026-11-13 Fri\n  (nothing)")
