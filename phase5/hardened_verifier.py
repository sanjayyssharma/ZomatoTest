from __future__ import annotations
import logging
from phase1.models import Restaurant
from phase2.models import EnrichedRestaurant, LLMRankingResponse

logger = logging.getLogger(__name__)

def hardened_validate_llm_output(
    llm_output: LLMRankingResponse, 
    candidates: list[Restaurant]
) -> list[EnrichedRestaurant]:
    """
    Stricter grounding checks. Ensure the LLM only recommends valid candidate IDs.
    """
    valid_ids = {c.restaurant_id: c for c in candidates if c.restaurant_id}
    validated: list[EnrichedRestaurant] = []
    
    for item in llm_output.ranked_items:
        if item.restaurant_id in valid_ids:
            restaurant = valid_ids[item.restaurant_id]
            validated.append(
                EnrichedRestaurant(
                    restaurant=restaurant,
                    explanation=item.explanation
                )
            )
        else:
            logger.warning(f"Hallucination detected: LLM returned invalid ID {item.restaurant_id}. Stripping from results.")
            
    if not validated:
        raise ValueError("LLM returned no valid grounded candidates.")
        
    return validated
