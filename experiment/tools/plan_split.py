#!/usr/bin/env python3
"""Decide Claude-vs-agy division of labor from measured data (2026-11-11 experiments), so the model does not re-derive it.

Usage:  plan_split.py '<json list>'   or   plan_split.py items.json
Item:   {"name": "...", "kind": KIND, "lines": est_lines_of_code, "testable": true, "judgment": false}
KIND:   backend | logic | bugfix | refactor | tests | frontend-visual | frontend-logic | docs
Output: one line per item + a batch verdict.

Model (fitted on the 2026-11-11 arms):  Claude saving (IET) ≈ 12 × offloaded_output_tokens − FIXED_OVERHEAD
  (12× not 5×: code Claude writes is re-read as context on every later turn)
  offloaded_output_tokens ≈ lines × TOKENS_PER_LINE[kind] × OFFLOAD_SHARE[kind]
  FIXED_OVERHEAD ≈ 35k IET (skill read + golden tests + report + extra turns), paid once per batch.
  Check: backend 470 lines → +44k predicted / +37–43k measured; large UI split → +13k / +16k; small UI → −18k / −55k.
"""
import json, sys

TOKENS_PER_LINE = {"frontend-logic": 34, "frontend-visual": 34}   # HTML/CSS/JS measured ~34 tok/line
DEFAULT_TPL = 20              # Python/backend measured ~20 output tokens per line (incl. tests)
MULT = 12
FIXED_OVERHEAD = 35_000       # IET per delegation batch
OFFLOAD_SHARE = {             # share of Claude's would-be output that agy can take over
    "backend": 0.70, "logic": 0.70, "bugfix": 0.6, "refactor": 0.8, "tests": 0.9, "docs": 0.8,
    "frontend-logic": 0.25,   # measured: Claude still writes design system/markup contract + golden tests
    "frontend-visual": 0.0,   # never delegate visual design (blind scores 5.6/10 vs 7–7.9)
}


def decide(items):
    out, batch = [], []
    for it in items:
        kind, lines = it.get("kind", "backend"), int(it.get("lines", 0))
        share = OFFLOAD_SHARE.get(kind, 0.5)
        reason = None
        if kind == "frontend-visual":
            reason = "visual design stays with Claude"
        elif not it.get("testable", True):
            reason = "not testable by automated tests"
        elif it.get("judgment"):
            reason = "needs design/security judgment"
        elif lines < 40:
            reason = "too small (<40 lines) — cheaper to write directly"
        gain = MULT * lines * TOKENS_PER_LINE.get(kind, DEFAULT_TPL) * share
        if reason:
            out.append((it, "CLAUDE", reason, 0))
        else:
            out.append((it, "AGY?", f"offloadable ≈ {gain/1000:.0f}k IET", gain))
            batch.append(gain)
    total = sum(batch)
    go = total > FIXED_OVERHEAD * 1.3      # 30% margin for variance (n=1 per arm)
    lines = []
    for it, who, why, g in out:
        if who == "AGY?":
            who = "AGY" if go else "CLAUDE"
            why += "" if go else " (batch too small)"
        lines.append(f"{who:6} {it.get('name','?'):<28} {it.get('kind'):<16} {it.get('lines'):>5} lines  {why}")
    verdict = (f"BATCH: delegate {len(batch)} item(s) in ONE delegate.py call (--parallel for independent ones); "
               f"expected Claude saving ≈ {(total - FIXED_OVERHEAD)/1000:.0f}k IET"
               if go else f"BATCH: do it yourself (offloadable {total/1000:.0f}k IET < break-even {FIXED_OVERHEAD*1.3/1000:.0f}k)")
    return "\n".join(lines + [verdict])


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "[]"
    items = json.loads(open(arg).read() if arg.endswith(".json") else arg)
    print(decide(items))
