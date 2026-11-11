---
name: agy-cowork
description: Cowork with Antigravity (agy CLI, Gemini) to save Claude tokens on implementation work. Use when a coding task has a clear written spec that can be checked by tests (CRUD, parsers, CLIs, APIs, glue code, bug fixes with known expected behavior, mechanical refactors, test backfill), or when the user asks to delegate to / cowork with Antigravity or Gemini.
---
# agy-cowork v3

Measured fact: Claude's cost is driven by the **number of turns × context size**, not by how much
code is written. Every extra tool call re-reads the whole context. So the whole job must be done in
**≤ 4 tool calls**. agy (Gemini) is the implementer, tester AND first-line reviewer; you only set the
contract and read one compact report.

`$COWORK` = repo holding `tools/`. Python w/ pytest: `$COWORK/.venv/bin/python`.

## When to delegate
Delegate when the spec already exists in writing (or you can state it in a few lines) and the
expected code is clearly larger than the spec. Do it yourself when the change is < ~40 lines or needs
design judgment you cannot write down briefly. Batch ALL delegable tasks into ONE call
(each agy call has ~25k tokens fixed overhead and every call costs you a turn).

## The 4-call recipe
1. **Read** (1 call): only the files you need to name signatures/types (e.g. models). Do not read specs
   you will pass through unchanged.
2. **Golden examples** (1 call, one Write): `tests/acceptance/test_golden.py` with 2–4 asserts per task
   that pin the *trickiest* rules (one happy path, one edge, one error). Not a full suite — agy writes that.
   Use the exact wording of the spec; double-check each expected value against the spec.
3. **Delegate** (1 call). Put specs with no dependency on each other in `--spec` with `--parallel`
   (each runs in its own git worktree concurrently — wall time matters because waits > 5 min expire
   your prompt cache); put specs that import/use those modules in `--then-spec` (run after the merge).
```
python3 $COWORK/tools/delegate.py --workdir <repo> --parallel \
  --spec <indepA.md> --spec <indepB.md> ... --then-spec <dependentC.md> ... \
  --accept "<python> -m pytest -q tests" --protect 'tests/acceptance/*' \
  --retries 2 --escalate-role worker_hard --audit --tag <label> > <repo>/.delegate_report.txt 2>&1
```
   Run it with Bash `run_in_background: true`, then **end your turn immediately without polling**
   (no sleep/tail/Monitor — each poll is a full-context turn). When notified, `cat` only the report file.
   `--audit` makes a fresh agy session review the diff against the specs and agy fix what it finds — zero Claude tokens.
4. **Decide from the report only** (0–1 call):
   - `ACCEPTED=True`, audit `NO_ISSUES` or only fixed items, no `WARNING` → done. Do NOT open code.
   - Worker says a protected test contradicts the spec → check that one assert against the spec and fix whichever is wrong.
   - `ACCEPTED=False` → read `acceptance tail`; fix a small bug yourself or re-delegate once with a sharper note.

Models are picked dynamically (`agy_models.py --role worker|worker_hard|planner`); never hard-code a model id.

## Quota
`delegate.py` exit **3** = Antigravity quota exhausted → stop and tell the user (they can switch accounts).
`python3 $COWORK/tools/agy_quota.py` shows quota at zero cost.
