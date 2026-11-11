---
name: agy-cowork
description: Cowork with Antigravity (agy CLI, Gemini) to save Claude tokens on implementation work. Use when a coding task has a clear spec that can be checked by tests (CRUD, parsers, CLIs, glue code, bug fixes with a known expected behavior, mechanical refactors, test backfill), or when the user asks to delegate to / cowork with Antigravity or Gemini.
---
# agy-cowork v1

You (Claude) are the **architect and gatekeeper**; agy is the **implementer**. You save tokens by
writing the *contract* (tests + short spec) yourself and letting agy write the code, then trusting
an automatic acceptance gate instead of reading the diff.

Tools (in `$COWORK` = this repo root): `tools/delegate.py`, `tools/agy_quota.py`, `tools/agy_models.py`.
Python for tests: `$COWORK/.venv/bin/python`.

## 1. Decide: delegate or do it yourself
Delegate when ALL hold: the behavior can be pinned down by tests; the change is mostly new code or
localized; no security-sensitive or architectural judgment is needed.
Do it yourself when: the change is < ~15 lines, needs cross-cutting design decisions, or the spec
would be longer than the code.

## 2. Write the contract (this is where your tokens go)
- Acceptance tests in `tests/acceptance/test_<task>.py`: cover every rule in the spec, especially
  error cases and edge cases. Tests are the real spec — agy is told not to edit them.
- Keep the spec file you pass short: point at the requirement text, state exact signatures.
- Batch related small tasks into ONE delegate call (each agy call has ~25k tokens fixed overhead).

## 3. Delegate
```
python3 $COWORK/tools/delegate.py --workdir <repo> --spec <spec.md> [--spec ...] \
  --accept "<python> -m pytest -q tests/acceptance/test_<task>.py" \
  --protect 'tests/acceptance/*' --retries 2 --escalate-role worker_hard --tag <label>
```
The model is picked dynamically (`agy_models.py --role worker`), never hard-code a model id.
For a hard design question you may ask `--role planner` (Argon/Carbon/Pro if quota allows; falls back automatically).

## 4. Review protocol (keep it cheap)
- Read ONLY the compact report. `ACCEPTED=True` + no `WARNING` → do not open the code, move on.
- Glance at `public=[...]`: unexpected public names → spot-check that one file only.
- `ACCEPTED=False` → read `acceptance tail`. Decide: fix the test if the test is wrong; tighten the
  spec and re-delegate once; or fix the remaining small bug yourself.
- Never read the full diff unless something above fails twice.

## 5. Quota
- `delegate.py` exits **3** = quota exhausted → stop delegating and tell the user (they can switch
  agy accounts). Check anytime: `python3 $COWORK/tools/agy_quota.py` (zero cost).
