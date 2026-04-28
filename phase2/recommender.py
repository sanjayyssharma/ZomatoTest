import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from phase1.filtering import generate_candidates
from phase1.io import load_restaurants
from phase1.models import Preferences, Restaurant
from phase1.ranking import rank_baseline
from phase2.llm import call_llm
from phase2.models import EnrichedRestaurant
from phase2.prompt import build_prompt
from phase2.verifier import validate_llm_output

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMRecommendationsResponse:
    preferences: Preferences
    final_preferences: Preferences
    relaxations_applied: list[str]
    total_restaurants: int
    candidate_count: int
    top: list[EnrichedRestaurant]
    used_llm: bool

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
            "used_llm": self.used_llm,
        }


def rank_with_llm(preferences: Preferences, candidates: list[Restaurant], top_k: int = 20) -> list[EnrichedRestaurant]:
    if not candidates:
        return []
        
    # Limit to top_k using baseline to avoid overflowing context
    baseline_ranked = rank_baseline(candidates)
    prompt_candidates = baseline_ranked[:top_k]
    
    prompt = build_prompt(preferences, prompt_candidates)
    
    try:
        llm_response = call_llm(prompt)
        validated = validate_llm_output(llm_response, prompt_candidates)
        return validated
    except Exception as e:
        logger.error(f"LLM ranking failed: {e}. Falling back to baseline.")
        # Fallback to baseline ranking, empty explanations
        return [EnrichedRestaurant(r, explanation="Fallback to baseline ranker.") for r in prompt_candidates]


def recommend(
    *,
    restaurants_jsonl: Path,
    preferences: Preferences,
    top_n: int = 10,
    min_candidates: int = 20,
) -> LLMRecommendationsResponse:
    restaurants = load_restaurants(restaurants_jsonl)
    candidates, relaxations, final_prefs = generate_candidates(
        restaurants=restaurants,
        prefs=preferences,
        min_candidates=min_candidates,
    )
    
    # We pass up to min_candidates candidates to the LLM (or more, but prompt limits it to avoid huge context)
    ranked = rank_with_llm(preferences, candidates, top_k=max(min_candidates, 20))
    top = ranked[:top_n]
    
    # check if we used LLM by checking the first explanation
    used_llm = bool(top and top[0].explanation != "Fallback to baseline ranker.")
    
    return LLMRecommendationsResponse(
        preferences=preferences,
        final_preferences=final_prefs,
        relaxations_applied=relaxations,
        total_restaurants=len(restaurants),
        candidate_count=len(candidates),
        top=top,
        used_llm=used_llm,
    )
