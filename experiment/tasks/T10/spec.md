# T10 — Stats report (`evtrack/stats.py`)
`compute_stats(tasks, today) -> dict` with keys:
- `total`, `open`, `done` (ints); `completion_rate` = done/total rounded to 3 decimals (0.0 when total is 0);
- `by_priority`: `{1: n, 2: n, 3: n}` counting **open** tasks (all three keys always present);
- `by_tag`: dict tag → number of open tasks having it (lowercased), ordered by count desc then tag asc;
- `overdue`: list of ids of open tasks with due < today, sorted by (due, id);
- `due_this_week`: ids of open tasks with today ≤ due ≤ today+6, sorted by (due, id);
- `oldest_open_id`: smallest id among open tasks or `None`.
`format_stats(stats) -> str` exactly:
```
Tasks: <total> (open <open>, done <done>, <pct>% complete)
Priority: p1=<n> p2=<n> p3=<n>
Tags: <tag>(<n>), <tag>(<n>) ...      ← top 5 from by_tag; "Tags: -" if none
Overdue: <id>, <id> ...               ← "Overdue: none" if empty
This week: <id>, <id> ...             ← "This week: none" if empty
```
where pct = completion_rate*100 formatted with one decimal (e.g. `66.7`). No trailing newline.
