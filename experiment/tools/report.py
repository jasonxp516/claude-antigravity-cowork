#!/usr/bin/env python3
"""Aggregate arms: Claude IET, agy tokens, hidden-test quality. Usage: report.py [--md]"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import claude_usage, eval_arm
ROOT = Path(__file__).resolve().parent.parent


def agy_for(tag):
    tot, calls = 0, 0
    if not tag: return 0, 0
    for l in open(ROOT / "metrics/runs.jsonl"):
        r = json.loads(l)
        if (r.get("tag") or "").startswith(tag):
            tot += (r.get("agy_usage") or {}).get("total_tokens", 0) or 0
            calls += len(r.get("attempts", [None]))
    return tot, calls


def main():
    arms = json.loads((ROOT / (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "metrics/arms.json")).read_text())
    rows = []
    for k, a in arms.items():
        cu = claude_usage.usage([a["transcript"]]) if Path(a["transcript"]).exists() else {"IET": None}
        sc = eval_arm.score(ROOT / a["ws"], a.get("tasks"))
        at, ac = agy_for(a.get("tag"))
        rows.append({"arm": k, "desc": a["desc"], "claude_IET": cu.get("IET"), "claude_out": cu.get("output_tokens"),
                     "claude_turns": cu.get("turns"), "agy_tokens": at, "agy_calls": ac,
                     "hidden": f'{sc["passed"]}/{sc["total"]}', "rate": sc["rate"], "by_task": {t: v["passed"] for t, v in sc["by_task"].items()}})
    base = next((r["claude_IET"] for r in rows if r["arm"].startswith("A")), None)
    print("| arm | desc | Claude IET | vs A | Claude out | turns | agy tokens | agy calls | hidden | by task |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        vs = f'{r["claude_IET"]/base:.0%}' if base and r["claude_IET"] else "-"
        print(f'| {r["arm"]} | {r["desc"]} | {r["claude_IET"]} | {vs} | {r["claude_out"]} | {r["claude_turns"]} | {r["agy_tokens"]} | {r["agy_calls"]} | {r["hidden"]} | {r["by_task"]} |')
    json.dump(rows, open(ROOT / "metrics" / ("report_rows_" + Path(sys.argv[1]).stem + ".json" if len(sys.argv) > 1 else "report_rows.json"), "w"), indent=1)

main()
