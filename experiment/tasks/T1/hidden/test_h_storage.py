import json
from datetime import date
import pytest
from evtrack.models import Task
from evtrack.storage import JsonStore


def test_add_get_list_persist(tmp_path):
    p = tmp_path / "s.json"
    s = JsonStore(p)
    assert s.list() == []
    a = s.add(Task("a")); b = s.add(Task("b", due=date(2026, 1, 1)))
    assert (a, b) == (1, 2)
    s2 = JsonStore(str(p))
    assert [t.title for t in s2.list()] == ["a", "b"]
    assert s2.get(2).due == date(2026, 1, 1)
    data = json.loads(p.read_text())
    assert data["next_id"] == 3 and len(data["tasks"]) == 2


def test_ids_not_reused(tmp_path):
    s = JsonStore(tmp_path / "s.json")
    s.add(Task("a")); s.add(Task("b")); s.delete(2)
    assert JsonStore(tmp_path / "s.json").add(Task("c")) == 3


def test_errors(tmp_path):
    s = JsonStore(tmp_path / "s.json")
    with pytest.raises(KeyError): s.get(1)
    with pytest.raises(KeyError): s.delete(1)
    with pytest.raises(ValueError): s.add(Task("x", id=5))
    s.add(Task("a"))
    with pytest.raises(ValueError): s.update(1, nope=1)
    with pytest.raises(ValueError): s.update(1, priority=7)
    assert JsonStore(tmp_path / "s.json").get(1).priority == 2


def test_update(tmp_path):
    s = JsonStore(tmp_path / "s.json")
    s.add(Task("a"))
    t = s.update(1, status="done", tags=["x"])
    assert t.status == "done" and JsonStore(tmp_path / "s.json").get(1).tags == ["x"]


def test_sorted_by_id(tmp_path):
    s = JsonStore(tmp_path / "s.json")
    for n in "abc": s.add(Task(n))
    s.update(1, title="z")
    assert [t.id for t in s.list()] == [1, 2, 3]
