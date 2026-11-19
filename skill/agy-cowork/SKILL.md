---
name: agy-cowork
description: Cowork with Antigravity (agy CLI, Gemini) to save Claude tokens on implementation work. Use when a coding task has a clear written spec that can be checked by tests (backend logic, CRUD, parsers, CLIs, APIs, glue code, bug fixes with known expected behavior, refactors, test backfill, large UI logic layers), or when the user asks to delegate to / cowork with Antigravity or Gemini.
---
# agy-cowork (v9, validated 2026-11-19 on Gemini 4)

Measured (2026-11-11, hidden tests + blind Opus UI scoring): backend batches cost **62–68%** of Claude-only with equal
hidden-test quality; naive outsourcing cost **188%**. Gemini 4 (2026-11-19): delegated backend code now scores *higher*
than Claude-only in blind review (Orchestrator 8–8.5, Neon 9, Hydrogen 7 vs Sonnet-only 5.5). Claude's cost = turns × context: every tool call re-reads the context, and code
you write yourself is re-read on every later turn. Long waits (> 5 min) expire the prompt cache. Do not re-derive this.

`$COWORK` = `~/.claude/skills/agy-cowork` (tools/: `delegate.py`, `plan_split.py`, `agy_quota.py`, `agy_models.py`,
`agy_trace.py`; `config/model_policy.json`; `frontend_rules.md`). Use the project's own Python/pytest in `--accept`.

## Step 0 — decide with the planner (1 call, no deliberation)
```
python3 $COWORK/tools/plan_split.py '[{"name":"…","kind":"backend|logic|bugfix|refactor|tests|docs|frontend-logic|frontend-visual","lines":N,"testable":true,"judgment":false}, …]'
```
Add `--subagent` if you are a subagent (5-min cache: a wait > 5 min costs one ~30k cache rewrite). Follow its verdict. Rules it encodes: break-even ≈ 300 backend lines per batch; < 40-line items, untestable work,
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
   `--preset backend` runs the **Orchestrator** (planner chosen by quota: Carbon/Argon/Neon; it executes with
   Hydrogen high in ONE session, so `--parallel` is off): T1–T6 blind review 8.5 (Argon) / 8 (Neon), 50/50 hidden,
   ~9 min, only ~2–4% of the Gemini 5h quota (+~2% Argon weekly). If no orchestrator has quota it falls back to
   Hydrogen high in parallel worktrees (blind 7, ~5 min, ~5% 5h). The wait is free for Claude in the main session
   (1h cache) — just end the turn. **In a subagent add `--fast`** (skip the orchestrator; ~5 min fits the 5-min cache).
   Use `--role worker_fast` only for trivial mechanical edits.
4. When notified, `cat` the report. `ACCEPTED=True`, audit `NO_ISSUES`/fixed, no `WARNING` → done, do NOT open code.
   Worker reports a spec conflict → check that one point. `ACCEPTED=False` → read the tail; fix small bug yourself or re-delegate once.

## Frontend
- **Visual design is Claude's by default.** 3.8 Flash UIs scored 5.6/10 twice; but on 2026-11-19 a Gemini 4 **Neon**
  UI built alone scored 8.5 vs Claude 8 (Hydrogen 7, Argon 5; one blind review, ±0.7 noise).
- **Small UI (≲ 300 lines)** → write it yourself with the design checklist, OR (tentative) let the `designer` role
  draft it: `delegate.py --role designer --audit --protect 'tests/acceptance/*' --spec <ui spec> --accept "<playwright golden tests>"`,
  then look only at screenshots (light/dark/mobile/error/empty) — do not read its code (it writes ~5× more lines than
  you would). If the screenshots miss the checklist, fix CSS yourself or rewrite.
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
- Models are picked dynamically by role from `agy models` + quota (`config/model_policy.json`): `orchestrator` =
  "Orchestrator (<Planner>)" by planner preference and quota; `worker_hard` = Hydrogen high (else newest Flash);
  `auditor` = Hydrogen high (the only model that caught a known bug in an audit test); `designer` = Neon high.
  Never hard-code model ids.
- Self-audit still misses bugs (Neon/Argon/Flash returned NO_ISSUES on code with 2 known bugs; Hydrogen found 1):
  spot-check important modules yourself.
- Decision logs (DECISIONS.md) from agy proved unreliable; use them only in deliberate tuning sessions.

## Quota
`delegate.py` exit **3** = agy quota exhausted → stop delegating and tell the user (they can switch agy accounts).
`python3 $COWORK/tools/agy_quota.py` shows quota at zero cost.
