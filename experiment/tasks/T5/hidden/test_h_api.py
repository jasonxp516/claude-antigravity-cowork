import io, json
from datetime import date
from evtrack.api import make_app
from evtrack.storage import JsonStore


def call(app, method, path, body=None, qs=""):
    raw = json.dumps(body).encode() if isinstance(body, (dict, list)) else (body or b"")
    env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": qs,
           "CONTENT_LENGTH": str(len(raw)), "CONTENT_TYPE": "application/json",
           "wsgi.input": io.BytesIO(raw), "SERVER_NAME": "x", "SERVER_PORT": "80", "wsgi.url_scheme": "http"}
    st = {}
    def sr(status, headers, exc_info=None): st["s"] = int(status.split()[0]); st["h"] = dict(headers)
    out = b"".join(app(env, sr))
    return st["s"], st["h"], (json.loads(out) if out else None)


def app(tmp_path):
    return make_app(JsonStore(tmp_path / "s.json"), today_fn=lambda: date(2026, 11, 10))


def test_crud(tmp_path):
    a = app(tmp_path)
    s, h, b = call(a, "POST", "/tasks", {"quick": "milk #home due:tomorrow"})
    assert s == 201 and b["id"] == 1 and b["due"] == "2026-11-11" and h["Content-Type"] == "application/json"
    call(a, "POST", "/tasks", {"quick": "report !1"})
    assert [t["id"] for t in call(a, "GET", "/tasks")[2]] == [1, 2]
    assert [t["id"] for t in call(a, "GET", "/tasks", qs="q=pri%3C%3D1")[2]] == [2]
    s, _, b = call(a, "PATCH", "/tasks/1", {"status": "done", "due": None})
    assert s == 200 and b["status"] == "done" and b["due"] is None
    s, _, b = call(a, "PATCH", "/tasks/2", {"due": "2027-01-01"})
    assert b["due"] == "2027-01-01"
    assert call(a, "GET", "/tasks/2")[0] == 200
    s, _, b = call(a, "DELETE", "/tasks/2"); assert s == 204 and b is None
    assert call(a, "GET", "/tasks/2")[0] == 404


def test_errors(tmp_path):
    a = app(tmp_path)
    assert call(a, "POST", "/tasks", b"{not json")[0] == 400
    assert call(a, "POST", "/tasks", {"quick": "x !9"})[0] == 400
    assert call(a, "GET", "/tasks", qs="q=foo%3Abar")[0] == 400
    assert call(a, "PATCH", "/tasks/7", {"status": "done"})[0] == 404
    call(a, "POST", "/tasks", {"quick": "x"})
    s, _, b = call(a, "PATCH", "/tasks/1", {"priority": 9}); assert s == 400 and "error" in b
    assert call(a, "GET", "/nope")[0] == 404
    assert call(a, "PUT", "/tasks")[0] == 405
    assert call(a, "POST", "/tasks/1")[0] == 405
