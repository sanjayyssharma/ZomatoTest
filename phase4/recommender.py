import logging
from pathlib import Path

from phase1.filtering import generate_candidates
from phase1.io import load_restaurants
from phase1.models import Preferences
from phase1.ranking import rank_baseline
from phase2.models import EnrichedRestaurant
from phase2.prompt import build_prompt
from phase2.verifier import validate_llm_output
from phase2.recommender import LLMRecommendationsResponse

from phase4.groq_llm import call_groq_llm
from phase4.instrumentation import track_latency, log_event

logger = logging.getLogger(__name__)

def rank_with_groq(preferences: Preferences, candidates: list, top_k: int = 20) -> list[EnrichedRestaurant]:
    if not candidates:
        return []
        
    with track_latency("baseline_pre_ranking", {"candidates": len(candidates)}):
        baseline_ranked = rank_baseline(candidates)
        prompt_candidates = baseline_ranked[:top_k]
    
    prompt = build_prompt(preferences, prompt_candidates)
    prompt += '\n\nIMPORTANT: Output valid JSON containing a single root key "ranked_items".'
    
    try:
        with track_latency("groq_llm_call", {"model": "llama3-8b-8192"}):
            llm_response = call_groq_llm(prompt)
            
        with track_latency("llm_validation"):
            validated = validate_llm_output(llm_response, prompt_candidates)
            
        log_event("groq_ranking_success", {"validated_count": len(validated)})
        return validated
    except Exception as e:
        logger.error(f"Groq LLM ranking failed: {e}. Falling back to baseline.")
        log_event("groq_ranking_fallback", {"error": str(e)})
        return [EnrichedRestaurant(r, explanation="Fallback to baseline ranker.") for r in prompt_candidates]

def recommend_with_groq(
    *,
    restaurants_jsonl: Path,
    preferences: Preferences,
    top_n: int = 10,
    min_candidates: int = 20,
) -> LLMRecommendationsResponse:
    with track_latency("load_restaurants"):
        restaurants = load_restaurants(restaurants_jsonl)
        
    with track_latency("generate_candidates"):
        candidates, relaxations, final_prefs = generate_candidates(
            restaurants=restaurants,
            prefs=preferences,
            min_candidates=min_candidates,
        )
    
    log_event("candidates_generated", {
        "count": len(candidates), 
        "relaxations": len(relaxations)
    })
    
    ranked = rank_with_groq(preferences, candidates, top_k=max(min_candidates, 20))
    top = ranked[:top_n]
    
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
