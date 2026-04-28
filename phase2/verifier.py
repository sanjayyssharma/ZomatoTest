import logging

from phase1.models import Restaurant
from phase2.models import EnrichedRestaurant, LLMRankingResponse

logger = logging.getLogger(__name__)


def validate_llm_output(
    llm_output: LLMRankingResponse, 
    candidates: list[Restaurant]
) -> list[EnrichedRestaurant]:
    candidate_map = {r.restaurant_id: r for r in candidates}
    
    validated = []
    seen_ids = set()
    
    for item in llm_output.ranked_items:
        if item.restaurant_id not in candidate_map:
            logger.warning(f"LLM returned unknown restaurant_id: {item.restaurant_id}")
            continue
            
        if item.restaurant_id in seen_ids:
            logger.warning(f"LLM returned duplicate restaurant_id: {item.restaurant_id}")
            continue
            
        if not item.explanation or len(item.explanation.strip()) < 5:
            logger.warning(f"LLM returned empty or too short explanation for {item.restaurant_id}")
            continue
            
        validated.append(
            EnrichedRestaurant(
                restaurant=candidate_map[item.restaurant_id],
                explanation=item.explanation.strip()
            )
        )
        seen_ids.add(item.restaurant_id)
        
    if not validated:
        raise ValueError("No valid candidates returned by LLM")
        
    return validated
