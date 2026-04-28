from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from pydantic import BaseModel, Field

from phase1.models import Preferences, Restaurant


class LLMRankedItem(BaseModel):
    restaurant_id: str = Field(description="The unique ID of the restaurant.")
    explanation: str = Field(description="A concise explanation of why this restaurant is a good fit based on the user's preferences.")


class LLMRankingResponse(BaseModel):
    ranked_items: list[LLMRankedItem] = Field(
        description="A list of ranked restaurants with explanations, ordered from best match to worst match."
    )


@dataclass(frozen=True)
class EnrichedRestaurant:
    restaurant: Restaurant
    explanation: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            **self.restaurant.to_json_dict(),
            "explanation": self.explanation,
        }
