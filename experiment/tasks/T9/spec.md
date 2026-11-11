# T9 — Recurring tasks & agenda (`evtrack/agenda.py`)
Tasks may carry recurrence via a tag `rec-<rule>` where rule is one accepted by `recur.next_occurrence`
(`rec-daily`, `rec-weekly`, `rec-monthly`, `rec-yearly`, `rec-every:3d` …). A task has at most one `rec-` tag (more → `ValueError` where encountered).
- `complete(store, id, today) -> Task | None`: mark the task done (`store.update`). If it has a `rec-` tag **and** a due date,
  also add a new open task copying title, priority and tags with `due = next_occurrence(old_due, rule)`; if that date is
  still `< today`, keep advancing until it is `>= today`. Returns the new task (or `None` if not recurring). Recurring task
  without due date → no new task. Already-done task → `ValueError`.
- `agenda(tasks, start, days=7) -> list[tuple[date, list[Task]]]`: for each day `start … start+days-1` (inclusive, `days ≥ 1`
  else `ValueError`) the open tasks due that day sorted by (priority, id); also, for open recurring tasks with a due date,
  include their **future virtual occurrences** (computed with `next_occurrence` from the due date) that fall in the window,
  as the same Task object. Overdue open tasks (due < start) are listed on the `start` day (only their actual due, not virtual
  occurrences before start). Days with no tasks are included with an empty list.
- `render_agenda(agenda_result) -> str`: one block per day: header `"YYYY-MM-DD Ddd"` (English 3-letter weekday, e.g. `2026-11-10 Tue`),
  then one line per task `"  - [p<priority>] <title>"` (append `" (overdue)"` if its actual due < that day and it is not a
  virtual occurrence); a day with no tasks has the single line `"  (nothing)"`. Blocks separated by one empty line; no trailing newline.
