# T3 — Query DSL (`evtrack/query.py`)
Implement `filter_tasks(tasks: list[Task], query: str) -> list[Task]` (returns a new list, input untouched).
Whitespace-separated terms, all ANDed:
- `status:open` / `status:done` (other values → `ValueError`)
- `tag:x` — task has tag x (case-insensitive). Multiple tag terms all required.
- `pri` comparison: `pri<N`, `pri<=N`, `pri=N`, `pri>=N`, `pri>N` (N integer).
- `due` comparison with same operators against `YYYY-MM-DD`; tasks with `due=None` never match a due comparison. `due:none` matches tasks without due date.
- `sort:field` / `sort:-field` where field ∈ {id, priority, due, title}; multiple sort terms = primary, secondary … in order written. Sorting by `due` puts `None` last regardless of direction. `title` sort is case-insensitive. Without sort terms keep the input order. Sort is stable.
- Any other `key:value` or unknown comparison key → `ValueError`.
- Any term without `:` or a comparison operator is free text: case-insensitive substring of title (multiple free words each required).
- Empty / whitespace query → all tasks.
