from datetime import date
import pytest
from evtrack.recur import next_occurrence as n


@pytest.mark.parametrize("d,r,e", [
    (date(2026, 12, 31), "daily", date(2027, 1, 1)),
    (date(2026, 12, 28), "weekly", date(2027, 1, 4)),
    (date(2026, 1, 31), "monthly", date(2026, 2, 28)),
    (date(2028, 1, 31), "monthly", date(2028, 2, 29)),
    (date(2026, 3, 31), "monthly", date(2026, 4, 30)),
    (date(2026, 12, 15), "monthly", date(2027, 1, 15)),
    (date(2028, 2, 29), "yearly", date(2029, 2, 28)),
    (date(2026, 5, 5), "yearly", date(2027, 5, 5)),
    (date(2026, 12, 30), "every:3d", date(2027, 1, 2)),
    (date(2026, 1, 1), "every:2w", date(2026, 1, 15)),
])
def test_ok(d, r, e):
    assert n(d, r) == e


@pytest.mark.parametrize("r", ["hourly", "every:0d", "every:3m", "every:xd", "every:"])
def test_bad(r):
    with pytest.raises(ValueError):
        n(date(2026, 1, 1), r)
