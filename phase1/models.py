from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class Restaurant:
    restaurant_id: str
    name: str
    location: str | None
    cuisines: list[str] = field(default_factory=list)
    rating: float | None = None
    cost_for_two: float | None = None

    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_json_dict(d: dict[str, Any]) -> "Restaurant":
        return Restaurant(
            restaurant_id=str(d.get("restaurant_id", "")),
            name=str(d.get("name", "")),
            location=d.get("location") if d.get("location") not in ("", None) else None,
            cuisines=list(d.get("cuisines") or []),
            rating=d.get("rating"),
            cost_for_two=d.get("cost_for_two"),
            raw=dict(d.get("raw") or {}),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


class BudgetBand(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


@dataclass(frozen=True)
class Preferences:
    location: str | None
    budget: BudgetBand | None
    cuisines: list[str]
    min_rating: float | None
    free_text: str | None = None

