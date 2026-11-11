"""Recurrence helper (contains bugs — see tasks/T6)."""
from datetime import date, timedelta


def next_occurrence(d: date, rule: str) -> date:
    """Return the next occurrence strictly after `d` for rule daily|weekly|monthly|yearly."""
    if rule == "daily":
        return d + timedelta(days=1)
    if rule == "weekly":
        return date(d.year, d.month, d.day + 7)
    if rule == "monthly":
        m = d.month + 1
        return date(d.year, m, d.day)
    if rule == "yearly":
        return date(d.year + 1, d.month, d.day)
    raise ValueError(rule)
