from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional

STATUSES = ("open", "done")
PRIORITIES = (1, 2, 3)  # 1 = highest


@dataclass
class Task:
    title: str
    id: Optional[int] = None
    status: str = "open"
    priority: int = 2
    tags: list[str] = field(default_factory=list)
    due: Optional[date] = None

    def __post_init__(self):
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if self.status not in STATUSES:
            raise ValueError(f"bad status {self.status!r}")
        if self.priority not in PRIORITIES:
            raise ValueError(f"bad priority {self.priority!r}")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["due"] = self.due.isoformat() if self.due else None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        d = dict(d)
        if d.get("due"):
            d["due"] = date.fromisoformat(d["due"])
        return cls(**d)
