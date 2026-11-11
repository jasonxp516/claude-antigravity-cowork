---
name: agy-cowork
description: Cowork with Antigravity (agy CLI, Gemini) to save Claude tokens on implementation work. Use when a coding task has a clear written spec that can be checked by tests (backend logic, CRUD, parsers, CLIs, APIs, glue code, bug fixes with known expected behavior, refactors, test backfill, large UI logic layers), or when the user asks to delegate to / cowork with Antigravity or Gemini.
---
# agy-cowork v6

Measured (2026-11-11, hidden tests + blind Opus UI scoring): backend batches cost **62–68%** of Claude-only with equal
quality; naive outsourcing cost **188%**. Claude's cost = turns × context: every tool call re-reads the context, and code
you write yourself is re-read on every later turn. Long waits (> 5 min) expire the prompt cache. Do not re-derive this.

`$COWORK` = repo holding `tools/` (`delegate.py`, `plan_split.py`, `agy_quota.py`, `agy_models.py`, `agy_trace.py`).

## Step 0 — decide with the planner (1 call, no deliberation)
```
python3 $COWORK/tools/plan_split.py '[{"name":"…","kind":"backend|logic|bugfix|refactor|tests|docs|frontend-logic|frontend-visual","lines":N,"testable":true,"judgment":false}, …]'
```
Follow its verdict. Rules it encodes: break-even ≈ 300 backend lines per batch; < 40-line items, untestable work,
security/architecture judgment and ALL visual design stay with Claude; batch everything delegable into ONE call.

## Backend / logic recipe (≤ 4 calls)
1. Read only files needed for signatures/types.
2. One Write: `tests/acceptance/test_golden.py` — 2–4 asserts per task pinning the trickiest rules (happy, edge, error),
   values double-checked against the spec. agy writes the full suite.
3. Delegate, background, then **end your turn without polling**:
```
python3 $COWORK/tools/delegate.py --preset backend --workdir <repo> --spec <a.md> --spec <b.md> [--then-spec <c.md>] \
  --accept "<python> -m pytest -q tests" --tag <label> > <repo>/.delegate_report.txt 2>&1      # Bash run_in_background
```
   `--then-spec` only for specs that import a module *created by another spec in this batch*.
4. When notified, `cat` the report. `ACCEPTED=True`, audit `NO_ISSUES`/fixed, no `WARNING` → done, do NOT open code.
   Worker reports a spec conflict → check that one point. `ACCEPTED=False` → read the tail; fix small bug yourself or re-delegate once.

## Frontend
- **Visual design is always Claude's** (Gemini-only UIs: 5.6/10 twice; Claude/hybrid: 6.9–7.9).
- **Small UI (≲ 300 lines)** → write it yourself with the design checklist. Delegation cost ~1.6× here.
- **Large UI → design-system split** (measured 91% cost, 7/7 tests, quality tie with Claude-only):
  1. You write `css/design.css` (tokens light/dark, spacing/type scale, every component class, states, responsive rules,
     comment index at top) + `index.html` shell + ONE complete reference view.
  2. Golden playwright tests for the key flows.
  3. `delegate.py --preset frontend-js --spec <spec> --spec <handoff note> --protect '<design.css>' …` — agy builds the
     other views' markup from your classes + all JS (preset attaches `frontend_rules.md`).
  4. One screenshot pass (light/dark/mobile), fix CSS yourself.
- **Handoff self-check before delegating** (a mismatch here caused the only hybrid test failure): every spec sentence
  about an id/testid matches your markup; a testid that must "show" a value wraps that value's text.
- Design checklist: `color-scheme: light dark` + styled native controls; one stable row layout (title line + meta line)
  surviving long titles at 375px; 16px mobile gutter; error text with context; distinct "no results for filter" state
  with a clear action vs truly empty; "x of y" counters when filtered; non-color cue for urgent states, never on future
  items; consistent badge treatment; quiet destructive buttons; vertical rhythm in forms; emoji may render as tofu → text/SVG.

## Reading the report
- `worker trace: … waste=NN%` > 20% = agy polled background jobs; harmless to you, but mention it if it recurs.
- Models are picked dynamically by role (`worker_fast` flash-low → `worker` → `worker_hard`; `planner` = Argon/Carbon/Pro
  only if quota allows). Never hard-code model ids.
- Decision logs (DECISIONS.md) from agy proved unreliable; use them only in deliberate tuning sessions.

## Quota
`delegate.py` exit **3** = agy quota exhausted → stop delegating and tell the user (they can switch agy accounts).
`python3 $COWORK/tools/agy_quota.py` shows quota at zero cost.
