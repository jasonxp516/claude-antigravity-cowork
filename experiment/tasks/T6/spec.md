# T6 — Fix `evtrack/recur.py`
`next_occurrence(d, rule)` returns the next occurrence strictly after `d`. Currently buggy. Required behavior:
- `daily` +1 day; `weekly` +7 days (across month/year boundaries).
- `monthly`: same day next month; if that day does not exist, clamp to the last day of that month (Jan 31 → Feb 28/29). Dec → Jan of next year.
- `yearly`: same date next year; Feb 29 → Feb 28 in non-leap years.
- Also support `every:Nd` (N ≥ 1 days) and `every:Nw` (N ≥ 1 weeks). Anything else → `ValueError`.
Do not change the function signature.
