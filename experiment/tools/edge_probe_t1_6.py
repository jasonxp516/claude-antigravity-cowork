"""Edge-case probe for T1–T6 (beyond hidden tests). Usage: python edge_probe_t1_6.py <arm dir>
Checks derived from the spec text (incl. bug classes found by the 2026-11-11 blind review), not from any arm's code."""
import sys, os, io, json, tempfile
from datetime import date
sys.path.insert(0, os.path.abspath(sys.argv[1]))
from evtrack.models import Task
from evtrack.storage import JsonStore
from evtrack import parser as P, query as Q, cli as C, api as A, recur as RC

R = []
def check(name, fn):
    try: ok = fn(); R.append((name, bool(ok), ""))
    except BaseException as e: R.append((name, False, f"{type(e).__name__}: {str(e)[:70]}"))
def raises(exc, fn, *a, **k):
    try: fn(*a, **k)
    except exc: return True
    return False
TD = date(2026, 3, 10)
def newstore(): return JsonStore(os.path.join(tempfile.mkdtemp(), "s.json"))

# --- T1
def ids_not_reused():
    s = newstore(); a = s.add(Task("a")); b = s.add(Task("b")); s.delete(b)
    s2 = JsonStore(s.path if hasattr(s, "path") else None) if False else None
    return a == 1 and b == 2 and s.add(Task("c")) == 3
check("T1 ids never reused after delete", ids_not_reused)
def ids_not_reused_reopen():
    p = os.path.join(tempfile.mkdtemp(), "s.json"); s = JsonStore(p); s.add(Task("a")); b = s.add(Task("b")); s.delete(b)
    return JsonStore(p).add(Task("c")) == 3 and json.load(open(p))["next_id"] in (4,)
check("T1 next_id persisted across reopen", ids_not_reused_reopen)
check("T1 add task with id -> ValueError", lambda: raises(ValueError, newstore().add, Task("a", id=5)))
def update_invalid_unchanged():
    p = os.path.join(tempfile.mkdtemp(), "s.json"); s = JsonStore(p); i = s.add(Task("a"))
    before = open(p).read()
    ok = raises(ValueError, s.update, i, priority=7) and raises(ValueError, s.update, i, bogus=1) and raises(ValueError, s.update, i, id=9)
    return ok and open(p).read() == before and s.get(i).priority == 2 and JsonStore(p).get(i).priority == 2
check("T1 invalid update raises and leaves store+file unchanged", update_invalid_unchanged)
def update_due_str():
    s = newstore(); i = s.add(Task("a"))
    try: s.update(i, due="2026-01-01")
    except ValueError: return True
    except Exception: return False
    return isinstance(s.get(i).due, date)  # converting is also acceptable
check("T1 update(due=str) -> ValueError or converted (not crash)", update_due_str)
check("T1 get/delete missing -> KeyError", lambda: raises(KeyError, newstore().get, 1) and raises(KeyError, newstore().delete, 1))
# --- T2
pq = lambda t: P.parse_quick(t, TD)
check("T2 bare # and #a.b are title words", lambda: pq("x # #a.b")["title"] == "x # #a.b" and pq("x # #a.b")["tags"] == [])
check("T2 tags lowercased+dedup keep order", lambda: pq("t #B #a #b")["tags"] == ["b", "a"])
check("T2 !4 / two priorities -> ValueError", lambda: raises(ValueError, pq, "t !4") and raises(ValueError, pq, "t !1 !2"))
check("T2 due:+0d, tomorrow", lambda: pq("t due:+0d")["due"] == TD and pq("t due:tomorrow")["due"] == date(2026, 3, 11))
check("T2 due:2026-02-30 / due:+-1d / two dues -> ValueError", lambda: raises(ValueError, pq, "t due:2026-02-30")
      and raises(ValueError, pq, "t due:+-1d") and raises(ValueError, pq, "t due:today due:today"))
check("T2 only tags -> empty title ValueError", lambda: raises(ValueError, pq, "#a !1"))
# --- T3
TS = [Task("beta", id=1, priority=2, tags=["Work"], due=date(2026, 3, 1)), Task("Alpha", id=2, priority=1),
      Task("gamma task", id=3, priority=3, tags=["home"], due=date(2026, 2, 1), status="done"), Task("alpha two", id=4, priority=2, due=date(2026, 4, 1))]
ids = lambda q: [t.id for t in Q.filter_tasks(TS, q)]
check("T3 due None last in both directions", lambda: ids("sort:due") == [3, 1, 4, 2] and ids("sort:-due") == [4, 1, 3, 2])
check("T3 multi sort + title case-insensitive", lambda: ids("sort:priority sort:-title") == [2, 1, 4, 3] and ids("sort:title") == [2, 4, 1, 3])
check("T3 tag case-insensitive both ways", lambda: ids("tag:work") == [1] and ids("tag:HOME") == [3])
check("T3 due:none and due comparisons", lambda: ids("due:none") == [2] and ids("due>=2026-03-01") == [1, 4])
check("T3 pri ops", lambda: ids("pri<2") == [2] and ids("pri>=2") == [1, 3, 4] and ids("pri=2") == [1, 4])
check("T3 unknown key / bad status / bad op value -> ValueError", lambda: raises(ValueError, ids, "foo:bar")
      and raises(ValueError, ids, "status:x") and raises(ValueError, ids, "pri<x"))
check("T3 free text AND, case-insensitive", lambda: ids("ALPHA two") == [4])
check("T3 input untouched + empty query", lambda: ids("   ") == [1, 2, 3, 4] and Q.filter_tasks(TS, "sort:-id") is not TS and [t.id for t in TS] == [1, 2, 3, 4])
# --- T4
def cli(*argv, path=None):
    o = io.StringIO(); rc = C.main(list(argv), path, today=TD, out=o); return rc, o.getvalue()
def cli_dash_words():
    p = os.path.join(tempfile.mkdtemp(), "s.json")
    rc, out = cli("add", "fix", "-v", "flag", path=p)
    return rc == 0 and JsonStore(p).get(1).title == "fix -v flag"
check("T4 add text containing '-v' token", cli_dash_words)
def cli_errors():
    p = os.path.join(tempfile.mkdtemp(), "s.json")
    r = [cli("done", "abc", path=p), cli("rm", "9", path=p), cli("list", "status:zzz", path=p), cli("add", "t", "!9", path=p)]
    return all(rc == 1 and o.startswith("error: ") for rc, o in r)
check("T4 errors -> rc1 'error: ' (non-int id, missing id, bad query, bad parse)", cli_errors)
def cli_list_fmt():
    p = os.path.join(tempfile.mkdtemp(), "s.json")
    cli("add", "Buy", "milk", "#home", "!1", "due:2026-03-12", path=p); cli("add", "x", path=p); cli("done", "2", path=p)
    rc, o = cli("list", path=p); rc2, o2 = cli("list", "nothingmatches", path=p)
    return o.splitlines() == ["  1 [ ] p1 Buy milk #home (due 2026-03-12)", "  2 [x] p2 x"] and o2.strip() == "no tasks"
check("T4 list format + 'no tasks'", cli_list_fmt)
# --- T5
def call(app, method, path, body=None, qs=""):
    raw = b"" if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": qs, "CONTENT_LENGTH": str(len(raw)),
           "CONTENT_TYPE": "application/json", "wsgi.input": io.BytesIO(raw), "SERVER_NAME": "x", "SERVER_PORT": "80", "wsgi.url_scheme": "http"}
    st = {}
    def sr(status, headers, exc=None): st["s"] = int(status.split()[0]); st["h"] = dict(headers)
    out = b"".join(app(env, sr)); return st["s"], st["h"], out
def mkapp():
    s = newstore(); s.add(Task("Buy milk", tags=["Home"])); return A.make_app(s, lambda: TD)
def api_patch_bad_types():
    app = mkapp()
    codes = [call(app, "PATCH", "/tasks/1", b)[0] for b in ({"title": 5}, {"due": "2026-13-01"}, {"due": 5}, {"priority": "1"}, {"bogus": 1}, [1, 2], {"id": 7})]
    return codes == [400] * 7
check("T5 PATCH wrong types/fields -> 400 (never 500)", api_patch_bad_types)
check("T5 PATCH invalid JSON -> 400", lambda: call(mkapp(), "PATCH", "/tasks/1", b"{nope")[0] == 400)
def api_patch_due():
    app = mkapp(); s1, _, b1 = call(app, "PATCH", "/tasks/1", {"due": "2026-04-01"}); s2, _, b2 = call(app, "PATCH", "/tasks/1", {"due": None})
    return s1 == 200 and json.loads(b1)["due"] == "2026-04-01" and s2 == 200 and json.loads(b2)["due"] is None
check("T5 PATCH due ISO / null", api_patch_due)
def api_routes():
    app = mkapp()
    r = [call(app, "PUT", "/tasks")[0], call(app, "GET", "/nope")[0], call(app, "GET", "/tasks/abc")[0], call(app, "GET", "/tasks/99")[0],
         call(app, "POST", "/tasks", {"nope": 1})[0], call(app, "POST", "/tasks", {"quick": "t !7"})[0], call(app, "DELETE", "/tasks/1/x")[0]]
    return r == [405, 404, 404, 404, 400, 400, 404]
check("T5 routing / status codes", api_routes)
def api_error_json():
    s, h, b = call(mkapp(), "GET", "/tasks/99")
    return h.get("Content-Type", "").startswith("application/json") and "error" in json.loads(b)
check("T5 error body is JSON with Content-Type", api_error_json)
def api_delete():
    app = mkapp(); s, h, b = call(app, "DELETE", "/tasks/1"); return s == 204 and b == b"" and call(app, "GET", "/tasks/1")[0] == 404
check("T5 DELETE 204 empty", api_delete)
check("T5 GET q= urlencoded, tag case-insensitive", lambda: len(json.loads(call(mkapp(), "GET", "/tasks", qs="q=tag%3Ahome")[2])) == 1)
check("T5 GET q= bad query -> 400", lambda: call(mkapp(), "GET", "/tasks", qs="q=status%3Azzz")[0] == 400)
# --- T6
n = RC.next_occurrence
check("T6 monthly clamp + leap + Dec", lambda: n(date(2024, 1, 31), "monthly") == date(2024, 2, 29) and n(date(2025, 1, 31), "monthly") == date(2025, 2, 28)
      and n(date(2025, 12, 15), "monthly") == date(2026, 1, 15) and n(date(2025, 3, 31), "monthly") == date(2025, 4, 30))
check("T6 yearly Feb29", lambda: n(date(2024, 2, 29), "yearly") == date(2025, 2, 28) and n(date(2023, 3, 1), "yearly") == date(2024, 3, 1))
check("T6 every:Nd/Nw", lambda: n(date(2025, 12, 30), "every:3d") == date(2026, 1, 2) and n(date(2025, 1, 1), "every:2w") == date(2025, 1, 15))
check("T6 invalid rules -> ValueError", lambda: all(raises(ValueError, n, date(2025, 1, 1), r) for r in ("every:0d", "every:3", "every:-1d", "every:2m", "hourly", "every:d")))

for nme, ok, err in R:
    print(("PASS " if ok else "FAIL ") + nme + (f"  [{err}]" if err else ""))
print(f"SCORE {sum(ok for _, ok, _ in R)}/{len(R)}")
