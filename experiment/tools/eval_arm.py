#!/usr/bin/env python3
"""Score an arm workspace against hidden tests. Usage: eval_arm.py runs/<arm> [--json]"""
import json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".venv/bin/python"
TOT = json.loads((ROOT / "tasks/hidden_totals.json").read_text())


def score(ws, tasks=None):
    res = {}
    for t in sorted((ROOT / "tasks").glob("*/hidden"), key=lambda x: (x.parent.name[0], int(x.parent.name[1:]))):
        if tasks and t.parent.name not in tasks:
            continue
        p = subprocess.run([str(PY), "-m", "pytest", "-q", "-p", "no:cacheprovider", str(t)], cwd=ws,
                           capture_output=True, text=True, timeout=300)
        last = (p.stdout.strip().splitlines() or [""])[-1]
        passed = int(m[1]) if (m := re.search(r"(\d+) passed", last)) else 0
        failed = sum(int(x) for x in re.findall(r"(\d+) (?:failed|error)", last))
        res[t.parent.name] = {"passed": min(passed, TOT[t.parent.name]), "total": TOT[t.parent.name]}
    tp = sum(v["passed"] for v in res.values()); tt = sum(v["total"] or 0 for v in res.values())
    return {"by_task": res, "passed": tp, "total": tt, "rate": round(tp / tt, 3)}


if __name__ == "__main__":
    tk = next((x.split("=")[1].split(",") for x in sys.argv if x.startswith("--tasks=")), None)
    r = score(sys.argv[1], tk)
    if "--json" in sys.argv:
        print(json.dumps(r))
    else:
        for k, v in r["by_task"].items():
            print(f"{k}: {v['passed']}/{v['total']}")
        print(f"TOTAL {r['passed']}/{r['total']} ({r['rate']:.1%})")
