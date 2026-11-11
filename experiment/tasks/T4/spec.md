# T4 — CLI (`evtrack/cli.py`)
Implement `main(argv: list[str], store_path, today=None, out=sys.stdout) -> int` using argparse
(`today` defaults to `date.today()`; uses `JsonStore`, `parse_to_task`, `filter_tasks` from T1–T3).
Subcommands:
- `add TEXT...` — joins TEXT words with spaces, parses with `parse_to_task`, stores; prints `added <id>`; returns 0.
- `list [QUERY...]` — joins words as query, prints one line per matching task: `"{id:>3} [{x}] p{priority} {title}"` where x is `x` for done else space, followed by ` #tag` for each tag and ` (due YYYY-MM-DD)` if due; returns 0. No matches → prints `no tasks`.
- `done ID` — mark done, prints `done <id>`; `rm ID` — delete, prints `removed <id>`.
- Errors (ValueError from parsing/query, missing id KeyError, non-integer ID) print `error: <message>` to `out` and return 1. Never raise for these.
