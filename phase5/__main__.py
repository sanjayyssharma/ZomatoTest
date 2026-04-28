import sys
import time
from pathlib import Path
from rich.console import Console

from dotenv import load_dotenv
load_dotenv()

from phase1.models import Preferences, BudgetBand
from phase1.preferences import validate_preferences
from phase5.recommender import recommend_with_indexed_groq

console = Console()

def main():
    prefs = Preferences(
        location="indiranagar",
        cuisines=["chinese"],
        budget=BudgetBand.medium, 
        min_rating=4.0,
    )
    prefs = validate_preferences(prefs)

    data_path = Path("artifacts/data/restaurants.jsonl")
    
    console.print(f"=== First Run (LLM Call) ===")
    t0 = time.time()
    resp1 = recommend_with_indexed_groq(
        restaurants_jsonl=data_path,
        preferences=prefs,
        top_n=5
    )
    t1 = time.time()
    console.print(f"Time taken: {t1-t0:.2f}s")
    for r in resp1.top:
        console.print(f"{r.restaurant.name} - {r.restaurant.rating}")

    console.print(f"\n=== Second Run (Cache Hit) ===")
    t2 = time.time()
    resp2 = recommend_with_indexed_groq(
        restaurants_jsonl=data_path,
        preferences=prefs,
        top_n=5
    )
    t3 = time.time()
    console.print(f"Time taken: {t3-t2:.2f}s")
    for r in resp2.top:
        console.print(f"{r.restaurant.name} - {r.restaurant.rating}")

if __name__ == "__main__":
    main()
