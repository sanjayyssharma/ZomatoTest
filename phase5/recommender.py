from __future__ import annotations
import logging
from pathlib import Path

from phase1.io import load_restaurants
from phase1.models import Preferences
from phase1.ranking import rank_baseline
from phase2.models import EnrichedRestaurant
from phase2.prompt import build_prompt
from phase2.recommender import LLMRecommendationsResponse

from phase4.groq_llm import call_groq_llm
from phase4.instrumentation import track_latency, log_event

from phase5.indexing import IndexedRestaurantStore
from phase5.cache import get_cached_llm_response, set_cached_llm_response
from phase5.hardened_verifier import hardened_validate_llm_output

logger = logging.getLogger(__name__)

# Basic in-memory caching for the loaded dataset across runs in the same process
_global_dataset = None
_global_store = None

def get_indexed_store(restaurants_jsonl: Path) -> IndexedRestaurantStore:
    global _global_dataset, _global_store
    if _global_store is None:
        with track_latency("load_and_index_restaurants"):
            _global_dataset = load_restaurants(restaurants_jsonl)
            _global_store = IndexedRestaurantStore(_global_dataset)
    return _global_store

def rank_with_groq_cached(preferences: Preferences, candidates: list, top_k: int = 20) -> list[EnrichedRestaurant]:
    if not candidates:
        return []
        
    with track_latency("baseline_pre_ranking", {"candidates": len(candidates)}):
        baseline_ranked = rank_baseline(candidates)
        prompt_candidates = baseline_ranked[:top_k]
    
    # Check cache first
    cached_response = get_cached_llm_response(preferences, prompt_candidates)
    if cached_response:
        log_event("groq_ranking_cache_hit", {})
        try:
            return hardened_validate_llm_output(cached_response, prompt_candidates)
        except Exception as e:
            logger.warning(f"Cached response invalid: {e}")
            # Fall through to call LLM

    # If no cache or invalid cache, call LLM
    prompt = build_prompt(preferences, prompt_candidates)
    prompt += '\n\nIMPORTANT: Output valid JSON containing a single root key "ranked_items".'
    
    try:
        with track_latency("groq_llm_call", {"model": "llama-3.1-8b-instant"}):
            llm_response = call_groq_llm(prompt)
            
        with track_latency("llm_validation"):
            validated = hardened_validate_llm_output(llm_response, prompt_candidates)
            
        # Cache successful responses
        set_cached_llm_response(preferences, prompt_candidates, llm_response)
        
        log_event("groq_ranking_success", {"validated_count": len(validated)})
        return validated
    except Exception as e:
        logger.error(f"Groq LLM ranking failed: {e}. Falling back to baseline.")
        log_event("groq_ranking_fallback", {"error": str(e)})
        return [EnrichedRestaurant(r, explanation="Fallback to baseline ranker.") for r in prompt_candidates]

def recommend_with_indexed_groq(
    *,
    restaurants_jsonl: Path,
    preferences: Preferences,
    top_n: int = 10,
    min_candidates: int = 20,
) -> LLMRecommendationsResponse:
    
    store = get_indexed_store(restaurants_jsonl)
        
    with track_latency("generate_candidates_indexed"):
        candidates, relaxations, final_prefs = store.generate_candidates(
            prefs=preferences,
            min_candidates=min_candidates,
        )
    
    log_event("candidates_generated", {
        "count": len(candidates), 
        "relaxations": len(relaxations)
    })
    
    ranked = rank_with_groq_cached(preferences, candidates, top_k=max(min_candidates, 20))
    top = ranked[:top_n]
    
    used_llm = bool(top and top[0].explanation != "Fallback to baseline ranker.")
    
    return LLMRecommendationsResponse(
        preferences=preferences,
        final_preferences=final_prefs,
        relaxations_applied=relaxations,
        total_restaurants=len(store.restaurants),
        candidate_count=len(candidates),
        top=top,
        used_llm=used_llm,
    )
