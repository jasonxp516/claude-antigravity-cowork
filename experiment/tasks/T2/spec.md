# T2 — Quick-add parser (`evtrack/parser.py`)
Implement `parse_quick(text: str, today: datetime.date) -> dict` returning keys `title, tags, priority, due`.
Tokens are whitespace-separated:
- `#word` → tag (`word` = `[A-Za-z0-9_-]+`, stored lowercase, deduplicated, original order kept). A bare `#` or `#` followed by other chars is a normal title word.
- `!1` `!2` `!3` → priority (default 2). Any other `!…` token (e.g. `!4`, `!x`) → `ValueError`. More than one priority token → `ValueError`.
- `due:YYYY-MM-DD` → that date; `due:today` → today; `due:tomorrow` → today+1; `due:+Nd` (N ≥ 0 integer) → today+N days. Any other `due:` value or invalid date → `ValueError`. More than one due token → `ValueError`. Default `None`.
- Remaining tokens, in order, joined by single spaces → `title`. Empty title → `ValueError`.
Also implement `parse_to_task(text, today) -> Task` building an `evtrack.models.Task` from the result.
