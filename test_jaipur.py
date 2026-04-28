import sys
from pathlib import Path
from rich.console import Console

from phase1.models import Preferences, BudgetBand
from phase1.preferences import validate_preferences
from phase4.recommender import recommend_with_groq

console = Console()

def run():
    path = Path("artifacts/data/restaurants.jsonl")
    if not path.exists():
        console.print("[red]Artifact missing[/red]")
        sys.exit(1)

    for loc in ["jaipur", "indiranagar"]:
        prefs = Preferences(
            location=loc,
            cuisines=[],
            budget=BudgetBand.medium, 
            min_rating=4.0,
        )
        prefs = validate_preferences(prefs)

        console.print(f"\n[bold blue]=== Testing Location: {loc.upper()} ===[/bold blue]")
        
        try:
            resp = recommend_with_groq(
                restaurants_jsonl=path,
                preferences=prefs,
                top_n=5,
                min_candidates=5
            )
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            continue

        console.print(f"[bold green]Used LLM:[/bold green] {resp.used_llm}")
        console.print(f"[bold green]Candidates Found:[/bold green] {resp.candidate_count}\n")
        
        if not resp.top:
            console.print("No restaurants found matching criteria. (Dataset may not cover this location).")
            continue

        for i, r in enumerate(resp.top):
            console.print(f"[bold]{i+1}. {r.restaurant.name}[/bold] ({r.restaurant.location})")
            console.print(f"   Rating: {r.restaurant.rating} | Cost for two: {r.restaurant.cost_for_two}")
            console.print(f"   Cuisines: {', '.join(r.restaurant.cuisines)}")
            console.print(f"   [dim]Why it fits:[/dim] {r.explanation}\n")

if __name__ == "__main__":
    run()
