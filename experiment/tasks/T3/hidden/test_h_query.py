from datetime import date
import pytest
from evtrack.models import Task
from evtrack.query import filter_tasks


def mk():
    return [Task("Buy milk", id=1, priority=2, tags=["Home"], due=date(2026, 11, 12)),
            Task("write report", id=2, priority=1, tags=["work"], status="done"),
            Task("call Bob", id=3, priority=3, tags=["home", "phone"], due=date(2026, 11, 11)),
            Task("buy stamps", id=4, priority=1, due=date(2026, 11, 12))]


def ids(r): return [t.id for t in r]


def test_empty():
    ts = mk(); assert ids(filter_tasks(ts, "  ")) == [1, 2, 3, 4]


def test_status_tag_text():
    assert ids(filter_tasks(mk(), "status:open tag:HOME")) == [1, 3]
    assert ids(filter_tasks(mk(), "tag:home tag:phone")) == [3]
    assert ids(filter_tasks(mk(), "BUY")) == [1, 4]
    assert ids(filter_tasks(mk(), "buy milk")) == [1]


def test_comparisons():
    assert ids(filter_tasks(mk(), "pri<=1")) == [2, 4]
    assert ids(filter_tasks(mk(), "pri>1 pri<3")) == [1]
    assert ids(filter_tasks(mk(), "due<2026-11-12")) == [3]
    assert ids(filter_tasks(mk(), "due>=2026-11-12")) == [1, 4]
    assert ids(filter_tasks(mk(), "due:none")) == [2]


def test_sort():
    assert ids(filter_tasks(mk(), "sort:priority sort:-id")) == [4, 2, 1, 3]
    assert ids(filter_tasks(mk(), "sort:due")) == [3, 1, 4, 2]
    assert ids(filter_tasks(mk(), "sort:-due")) == [1, 4, 3, 2]
    assert ids(filter_tasks(mk(), "sort:title")) == [1, 4, 3, 2]


def test_input_untouched():
    ts = mk(); filter_tasks(ts, "sort:-id"); assert ids(ts) == [1, 2, 3, 4]


@pytest.mark.parametrize("q", ["status:closed", "foo:bar", "sort:nope", "size>3"])
def test_errors(q):
    with pytest.raises(ValueError):
        filter_tasks(mk(), q)
