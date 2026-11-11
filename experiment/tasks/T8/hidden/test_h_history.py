import pytest
from evtrack.models import Task
from evtrack.storage import JsonStore
from evtrack.history import HistoryStore


def hs(p, **kw): return HistoryStore(JsonStore(p), **kw)


def test_add_undo_redo_same_id(tmp_path):
    p = tmp_path / "s.json"; h = hs(p)
    assert h.add(Task("a")) == 1
    assert h.undo() == "undo add 1" and h.list() == []
    assert h.redo() == "redo add 1" and h.get(1).title == "a"
    assert h.add(Task("b")) == 2


def test_update_delete(tmp_path):
    h = hs(tmp_path / "s.json")
    h.add(Task("a", tags=["x"]))
    h.update(1, title="b", priority=1)
    h.delete(1)
    assert h.undo() == "undo delete 1" and h.get(1).title == "b"
    assert h.undo() == "undo update 1"
    t = h.get(1); assert (t.title, t.priority, t.tags) == ("a", 2, ["x"])
    assert h.redo() == "redo update 1" and h.get(1).title == "b"


def test_errors_and_stacks(tmp_path):
    h = hs(tmp_path / "s.json")
    assert not h.can_undo() and not h.can_redo()
    with pytest.raises(IndexError): h.undo()
    with pytest.raises(IndexError): h.redo()
    h.add(Task("a"))
    with pytest.raises(ValueError): h.update(1, priority=9)
    with pytest.raises(KeyError): h.delete(5)
    assert h.undo() == "undo add 1" and not h.can_undo() and h.can_redo()
    h.add(Task("c"))
    assert not h.can_redo()


def test_ids_never_reused(tmp_path):
    h = hs(tmp_path / "s.json")
    h.add(Task("a")); h.add(Task("b")); h.undo()   # remove 2
    assert h.add(Task("c")) == 3


def test_limit(tmp_path):
    h = hs(tmp_path / "s.json", limit=2)
    for n in "abc": h.add(Task(n))
    h.undo(); h.undo()
    with pytest.raises(IndexError): h.undo()
    assert [t.id for t in h.list()] == [1]


def test_persisted(tmp_path):
    p = tmp_path / "s.json"
    h = hs(p); h.add(Task("a")); h.update(1, title="z")
    assert (tmp_path / "s.json.history.json").exists()
    h2 = hs(p)
    assert h2.undo() == "undo update 1" and h2.get(1).title == "a"
    h3 = hs(p)
    assert h3.redo() == "redo update 1" and JsonStore(p).get(1).title == "z"
