from phase1.models import Preferences, Restaurant


def build_prompt(preferences: Preferences, candidates: list[Restaurant]) -> str:
    pref_lines = []
    if preferences.location:
        pref_lines.append(f"- Location: {preferences.location}")
    if preferences.budget:
        pref_lines.append(f"- Budget: {preferences.budget.value}")
    if preferences.cuisines:
        pref_lines.append(f"- Cuisines: {', '.join(preferences.cuisines)}")
    if preferences.min_rating:
        pref_lines.append(f"- Minimum Rating: {preferences.min_rating}")
    if preferences.free_text:
        pref_lines.append(f"- Additional Preferences: {preferences.free_text}")

    prefs_str = "\n".join(pref_lines) if pref_lines else "- No specific preferences provided."

    cand_lines = []
    for r in candidates:
        rating = "N/A" if r.rating is None else f"{r.rating:.1f}"
        cost = "N/A" if r.cost_for_two is None else f"{int(r.cost_for_two)}"
        cuisines = ", ".join(r.cuisines)
        cand_lines.append(
            f"ID: {r.restaurant_id} | Name: {r.name} | Rating: {rating} | Cost for two: {cost} | Cuisines: {cuisines} | Location: {r.location}"
        )
    
    candidates_str = "\n".join(cand_lines)
    
    return f"""You are an expert AI restaurant recommender. 

User Preferences:
{prefs_str}

Candidate Restaurants:
{candidates_str}

Task: 
Rank the candidate restaurants based on how well they match the user's preferences.
Return a structured list of `ranked_items` containing the `restaurant_id` and a concise `explanation` for each chosen restaurant.
The explanation should highlight specific features (like cuisine, rating, or matching free-text) that make it a good fit. 
Ensure you only use the provided candidate IDs.
"""
