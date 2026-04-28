from __future__ import annotations
import diskcache as dc
from pathlib import Path
import json
import hashlib
from phase1.models import Preferences, Restaurant
from phase2.models import LLMRankingResponse

# Setup diskcache
CACHE_DIR = Path("artifacts/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
llm_cache = dc.Cache(str(CACHE_DIR / "llm"))

def _hash_preferences_and_candidates(prefs: Preferences, candidates: list[Restaurant]) -> str:
    # Create a deterministic representation
    prefs_dict = {
        "location": prefs.location,
        "budget": prefs.budget.value if prefs.budget else None,
        "min_rating": prefs.min_rating,
        "cuisines": sorted(prefs.cuisines),
    }
    cand_ids = sorted([r.restaurant_id for r in candidates if r.restaurant_id])
    
    data = json.dumps({"prefs": prefs_dict, "candidates": cand_ids}, sort_keys=True)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def get_cached_llm_response(prefs: Preferences, candidates: list[Restaurant]) -> LLMRankingResponse | None:
    key = _hash_preferences_and_candidates(prefs, candidates)
    cached_data = llm_cache.get(key)
    if cached_data:
        try:
            return LLMRankingResponse.model_validate_json(cached_data)
        except Exception:
            return None
    return None

def set_cached_llm_response(prefs: Preferences, candidates: list[Restaurant], response: LLMRankingResponse):
    key = _hash_preferences_and_candidates(prefs, candidates)
    llm_cache.set(key, response.model_dump_json())
