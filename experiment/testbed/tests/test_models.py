from datetime import date
import pytest
from evtrack.models import Task


def test_roundtrip():
    t = Task("x", id=1, tags=["a"], due=date(2026, 1, 2))
    assert Task.from_dict(t.to_dict()) == t


def test_validation():
    with pytest.raises(ValueError):
        Task(" ")
    with pytest.raises(ValueError):
        Task("x", priority=5)
