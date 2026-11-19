"""Edge-case probe for T7–T10 (beyond hidden tests). Usage: python edge_probe_t7_10.py <arm dir>
Each check prints PASS/FAIL; checks are derived from the spec text, not from any arm's code."""
import sys, os, tempfile, traceback
from datetime import date, timedelta
sys.path.insert(0, os.path.abspath(sys.argv[1]))
from evtrack.models import Task
from evtrack import io_formats as io, stats as st, agenda as ag
from evtrack.storage import JsonStore
from evtrack.history import HistoryStore

R = []
def _id(x): return x if isinstance(x, int) else x.id
def check(name, fn):
    try:
        ok = fn(); R.append((name, bool(ok), ""))
    except Exception as e:
        R.append((name, False, f"{type(e).__name__}: {str(e)[:80]}"))

T = lambda **k: Task(**{"title": "t", **k})
# --- T7
def ics_roundtrip_specials():
    ts = [T(id=1, title="a;b,c\\d\nnew line", tags=["x,y", "z;w"])]
    back = io.from_ics(io.to_ics(ts))
    return back[0].title == ts[0].title and back[0].tags == ts[0].tags
check("ics roundtrip escapes + U+2028", ics_roundtrip_specials)
def ics_fold_utf8():
    t = io.to_ics([T(id=1, title="測試" * 60 + "é" * 30)])
    lines = t.split("\r\n")
    okl = all(len(l.encode()) <= 75 for l in lines)
    return okl and io.from_ics(t)[0].title == "測試" * 60 + "é" * 30
check("ics fold <=75 octets + roundtrip CJK", ics_fold_utf8)
check("ics accepts tab continuation", lambda: io.from_ics(
    "BEGIN:VCALENDAR\nBEGIN:VTODO\nSUMMARY:ab\n\tcd\nEND:VTODO\nEND:VCALENDAR\n")[0].title == "abcd")
check("ics priority 0 -> 2, 4 -> 1, 6 -> 3", lambda: [x.priority for x in io.from_ics(
    "BEGIN:VCALENDAR\r\n" + "".join(f"BEGIN:VTODO\r\nSUMMARY:s\r\nPRIORITY:{p}\r\nEND:VTODO\r\n" for p in (0, 4, 6)) +
    "END:VCALENDAR\r\n")] == [2, 1, 3])
def ics_no_summary():
    try: io.from_ics("BEGIN:VCALENDAR\r\nBEGIN:VTODO\r\nSTATUS:COMPLETED\r\nEND:VTODO\r\nEND:VCALENDAR\r\n")
    except ValueError: return True
    return False
check("ics VTODO without SUMMARY -> ValueError", ics_no_summary)
def csv_roundtrip():
    ts = [T(id=3, title='He said "hi", ok\nline2', tags=["a", "b"], due=date(2026, 2, 3)), T(id=4, title="x")]
    b = io.from_csv(io.to_csv(ts))
    return [(x.title, x.tags, x.due, x.id) for x in b] == [(ts[0].title, ["a", "b"], date(2026, 2, 3), None), ("x", [], None, None)]
check("csv roundtrip quotes/newline, ids dropped", csv_roundtrip)
def csv_row_num():
    try: io.from_csv("id,title,status,priority,tags,due\n1,a,open,2,,\n2,b,open,7,,\n")
    except ValueError as e: return "row 2" in str(e)
    return False
check("csv bad row reports 'row 2'", csv_row_num)
def csv_bad_header():
    try: io.from_csv("id,title,status,priority,tag,due\n")
    except ValueError: return True
    return False
check("csv wrong header -> ValueError", csv_bad_header)
# --- T8
def hist_persist_and_ids():
    d = tempfile.mkdtemp(); p = os.path.join(d, "s.json")
    h = HistoryStore(JsonStore(p)); a = _id(h.add(T(title="a"))); b = _id(h.add(T(title="b")))
    h.undo()                                   # undo add b
    h2 = HistoryStore(JsonStore(p)); h2.redo()  # new instance must redo
    c = _id(h2.add(T(title="c")))
    ids = sorted(x.id for x in h2.list())
    return ids == [a, b, c] and c > b
check("history persisted across instances; ids not reused", hist_persist_and_ids)
def hist_failed_no_push():
    d = tempfile.mkdtemp(); h = HistoryStore(JsonStore(os.path.join(d, "s.json")))
    a = _id(h.add(T(title="a")))
    try: h.update(a, priority=9)
    except Exception: pass
    try: h.delete(999)
    except Exception: pass
    h.undo()
    return not h.can_undo() and h.list() == []
check("history: failed calls push nothing", hist_failed_no_push)
def hist_limit():
    d = tempfile.mkdtemp(); h = HistoryStore(JsonStore(os.path.join(d, "s.json")), limit=2)
    for i in range(4): h.add(T(title=f"x{i}"))
    h.undo(); h.undo()
    return not h.can_undo() and len(h.list()) == 2
check("history limit drops oldest", hist_limit)
def hist_undo_update_all_fields():
    d = tempfile.mkdtemp(); h = HistoryStore(JsonStore(os.path.join(d, "s.json")))
    a = _id(h.add(T(title="a", tags=["q"], due=date(2026, 1, 1))))
    h.update(a, title="b", tags=["r", "s"], due=None, priority=1)
    r = h.undo(); g = h.get(a)
    return r == f"undo update {a}" and (g.title, g.tags, g.due, g.priority) == ("a", ["q"], date(2026, 1, 1), 2)
check("history undo update restores all fields", hist_undo_update_all_fields)
# --- T9
def store_with(*tasks):
    s = JsonStore(os.path.join(tempfile.mkdtemp(), "s.json"))
    return s, [s.get(_id(s.add(t))) for t in tasks]
def complete_catchup():
    s, (a,) = store_with(T(title="r", tags=["rec-weekly"], due=date(2026, 1, 1)))
    n = ag.complete(s, a.id, date(2026, 1, 20))
    return n.due == date(2026, 1, 22) and s.get(a.id).status == "done"
check("complete advances past today", complete_catchup)
def complete_twice():
    s, (a,) = store_with(T(title="r", due=date(2026, 1, 1)))
    ag.complete(s, a.id, date(2026, 1, 2))
    try: ag.complete(s, a.id, date(2026, 1, 2))
    except ValueError: return True
    return False
check("complete already-done -> ValueError", complete_twice)
def two_rec_tags():
    s, (a,) = store_with(T(title="r", tags=["rec-daily", "rec-weekly"], due=date(2026, 1, 1)))
    try: ag.complete(s, a.id, date(2026, 1, 2))
    except ValueError: return True
    return False
check("two rec- tags -> ValueError", two_rec_tags)
def agenda_overdue_virtual():
    t = T(id=1, title="r", tags=["rec-daily"], due=date(2026, 1, 1))
    res = ag.agenda([t], date(2026, 1, 3), days=3)
    counts = [len(x[1]) for x in res]
    txt = ag.render_agenda(res)
    return counts == [2, 1, 1] and txt.count("(overdue)") == 1 and not txt.endswith("\n")
check("agenda: overdue on start + virtual occurrences, single (overdue)", agenda_overdue_virtual)
def agenda_days0():
    try: ag.agenda([], date(2026, 1, 1), days=0)
    except ValueError: return True
    return False
check("agenda days=0 -> ValueError", agenda_days0)
check("render empty day + weekday", lambda: ag.render_agenda(ag.agenda([], date(2026, 11, 10), 1)) == "2026-11-10 Tue\n  (nothing)")
# --- T10
def stats_tags_case():
    ts = [T(id=1, tags=["Work"]), T(id=2, tags=["work", "home"]), T(id=3, tags=["WORK", "work"]), T(id=4, status="done", tags=["home"])]
    s = st.compute_stats(ts, date(2026, 1, 1))
    return list(s["by_tag"].items()) == [("work", 3), ("home", 1)]
check("stats tags lowercased, counted once per task", stats_tags_case)
def stats_empty():
    s = st.compute_stats([], date(2026, 1, 1)); f = st.format_stats(s)
    return s["completion_rate"] == 0.0 and s["by_priority"] == {1: 0, 2: 0, 3: 0} and f == (
        "Tasks: 0 (open 0, done 0, 0.0% complete)\nPriority: p1=0 p2=0 p3=0\nTags: -\nOverdue: none\nThis week: none")
check("stats empty + exact format", stats_empty)
def stats_week_bounds():
    td = date(2026, 1, 1)
    ts = [T(id=i, due=td + timedelta(days=d)) for i, d in ((1, -1), (2, 0), (3, 6), (4, 7))] + [T(id=5, status="done", due=td - timedelta(days=3))]
    s = st.compute_stats(ts, td)
    return s["overdue"] == [1] and s["due_this_week"] == [2, 3] and s["oldest_open_id"] == 1
check("stats overdue/this-week boundaries", stats_week_bounds)
check("stats pct 66.7", lambda: "66.7% complete" in st.format_stats(st.compute_stats(
    [T(id=1, status="done"), T(id=2, status="done"), T(id=3)], date(2026, 1, 1))))

for n, ok, err in R:
    print(("PASS " if ok else "FAIL ") + n + (f"  [{err}]" if err else ""))
print(f"SCORE {sum(ok for _, ok, _ in R)}/{len(R)}")
