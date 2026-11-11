import io
from datetime import date
from evtrack.cli import main
T = date(2026, 11, 10)


def run(args, p):
    out = io.StringIO(); rc = main(args, p, today=T, out=out); return rc, out.getvalue()


def test_flow(tmp_path):
    p = tmp_path / "s.json"
    assert run(["add", "Buy", "milk", "#home", "due:tomorrow"], p) == (0, "added 1\n")
    assert run(["add", "report !1"], p)[1] == "added 2\n"
    rc, o = run(["list"], p)
    assert rc == 0 and o.splitlines() == ["  1 [ ] p2 Buy milk #home (due 2026-11-11)", "  2 [ ] p1 report"]
    assert run(["done", "2"], p) == (0, "done 2\n")
    assert run(["list", "status:done"], p)[1] == "  2 [x] p1 report\n"
    assert run(["rm", "1"], p) == (0, "removed 1\n")
    assert run(["list", "milk"], p) == (0, "no tasks\n")


def test_errors(tmp_path):
    p = tmp_path / "s.json"
    for args in (["done", "9"], ["rm", "abc"], ["add", "x", "!9"], ["list", "foo:bar"]):
        rc, o = run(args, p)
        assert rc == 1 and o.startswith("error: "), args
