from datetime import date
import pytest
from evtrack.models import Task
from evtrack.io_formats import to_csv, from_csv, to_ics, from_ics


def mk():
    return [Task("Buy milk, eggs", id=1, tags=["home", "shop"], due=date(2026, 11, 12)),
            Task('say "hi"; then\\leave', id=2, priority=1, status="done"),
            Task("x", id=3, priority=3)]


def strip(ts):
    return [Task(**{**t.to_dict(), "id": None, "due": t.due}) for t in ts]


def test_csv_roundtrip():
    s = to_csv(mk())
    assert s.splitlines()[0] == "id,title,status,priority,tags,due"
    assert s.splitlines()[1] == '1,"Buy milk, eggs",open,2,home;shop,2026-11-12'
    assert from_csv(s) == strip(mk())


def test_csv_errors():
    with pytest.raises(ValueError):
        from_csv("id,title\n1,a\n")
    bad = "id,title,status,priority,tags,due\n1,a,open,2,,\n2,b,open,7,,\n"
    with pytest.raises(ValueError, match="row 2"):
        from_csv(bad)


def test_ics_format():
    s = to_ics(mk())
    assert s.endswith("\r\n") and s.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//evtrack//EN\r\n")
    L = s.split("\r\n")
    assert "SUMMARY:Buy milk\\, eggs" in L and "CATEGORIES:home,shop" in L and "DUE;VALUE=DATE:20261112" in L
    assert "SUMMARY:say \"hi\"\; then\\\\leave" in L and "STATUS:COMPLETED" in L and "PRIORITY:1" in L
    assert "PRIORITY:9" in L and "UID:evtrack-1@local" in L
    assert L.count("BEGIN:VTODO") == 3 and L[-2] == "END:VCALENDAR"
    assert "UID:evtrack-new-1@local" in to_ics([Task("a", id=4), Task("b")])


def test_ics_folding_utf8():
    t = Task("任務" * 40, id=1)
    s = to_ics([t])
    lines = s.split("\r\n")
    for l in lines:
        assert len(l.encode()) <= 75
    i = [k for k, l in enumerate(lines) if l.startswith("SUMMARY:")][0]
    assert lines[i + 1].startswith(" ") and len(lines[i].encode()) <= 75
    assert from_ics(s)[0].title == t.title


def test_ics_roundtrip_and_lenient():
    assert from_ics(to_ics(mk())) == strip(mk())
    txt = "BEGIN:VCALENDAR\nBEGIN:VTODO\nSUMMARY:long\n  title\nPRIORITY:6\nX-FOO:bar\nEND:VTODO\nEND:VCALENDAR\n"
    t = from_ics(txt)[0]
    assert t.title == "long title" and t.priority == 3 and t.status == "open"
    with pytest.raises(ValueError):
        from_ics("BEGIN:VCALENDAR\nBEGIN:VTODO\nPRIORITY:1\nEND:VTODO\nEND:VCALENDAR\n")
