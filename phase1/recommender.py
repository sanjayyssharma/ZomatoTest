from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from phase1.filtering import generate_candidates
from phase1.io import load_restaurants
from phase1.models import Preferences, Restaurant
from phase1.ranking import rank_baseline


@dataclass(frozen=True)
class RecommendationsResponse:
    preferences: Preferences
    final_preferences: Preferences
    relaxations_applied: list[str]
    total_restaurants: int
    candidate_count: int
    top: list[Restaurant]

    def to_json_dict(self) -> dict[str, Any]:
        def prefs_dict(p: Preferences) -> dict[str, Any]:
            return {
                "location": p.location,
                "budget": None if p.budget is None else p.budget.value,
                "cuisines": list(p.cuisines),
                "min_rating": p.min_rating,
                "free_text": p.free_text,
            }

        return {
            "preferences": prefs_dict(self.preferences),
            "final_preferences": prefs_dict(self.final_preferences),
            "relaxations_applied": list(self.relaxations_applied),
            "total_restaurants": self.total_restaurants,
            "candidate_count": self.candidate_count,
            "top": [r.to_json_dict() for r in self.top],
        }


def recommend(
    *,
    restaurants_jsonl: Path,
    preferences: Preferences,
    top_n: int = 10,
    min_candidates: int = 20,
) -> RecommendationsResponse:
    restaurants = load_restaurants(restaurants_jsonl)
    candidates, relaxations, final_prefs = generate_candidates(
        restaurants=restaurants,
        prefs=preferences,
        min_candidates=min_candidates,
    )
    ranked = rank_baseline(candidates)
    top = ranked[:top_n]
    return RecommendationsResponse(
        preferences=preferences,
        final_preferences=final_prefs,
        relaxations_applied=relaxations,
        total_restaurants=len(restaurants),
        candidate_count=len(candidates),
        top=top,
    )

