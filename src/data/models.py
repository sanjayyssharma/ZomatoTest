from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Restaurant:
    restaurant_id: str
    name: str
    location: str | None = None
    cuisines: list[str] = field(default_factory=list)
    rating: float | None = None
    cost_for_two: float | None = None

    raw: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)

