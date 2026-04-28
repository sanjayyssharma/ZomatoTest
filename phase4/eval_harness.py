import os
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

from dotenv import load_dotenv
load_dotenv()

from groq import Groq

from phase1.models import Preferences
from phase1.preferences import parse_budget, parse_cuisines, parse_min_rating, validate_preferences
from phase4.recommender import recommend_with_groq

GOLDEN_QUERIES = [
    {"location": "BTM", "budget": "low", "cuisines": "south indian", "min_rating": "4.0", "free_text": "Good for quick breakfast"},
    {"location": "Indiranagar", "budget": "high", "cuisines": "italian", "min_rating": "4.5", "free_text": "Romantic fine dining"},
    {"location": "Banashankari", "budget": "medium", "cuisines": "chinese, north indian", "min_rating": "3.5", "free_text": "Spicy food"},
]

def evaluate_explanation_with_groq(query: dict, explanation: str, restaurant_name: str) -> int:
    """Uses Groq LLM as a judge to score the explanation on a scale of 1-5."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return 0 # Cannot evaluate
        
    client = Groq(api_key=api_key)
    prompt = f"""Evaluate the relevance of the following explanation for a restaurant recommendation.
User Query: {json.dumps(query)}
Restaurant Name: {restaurant_name}
Explanation: {explanation}

Score the explanation from 1 to 5 based on how well it addresses the user's specific preferences (location, budget, cuisines, free text). 
1 = Irrelevant or generic (e.g. 'Fallback to baseline ranker.')
5 = Highly specific, relevant, and grounded in the restaurant's features.

Return ONLY a JSON object with a 'score' integer field. Example: {{"score": 4}}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = json.loads(response.choices[0].message.content)
        return content.get("score", 0)
    except Exception:
        return 0

def run_eval():
    console = Console()
    console.print("[bold]Running Phase 4 Evaluation Harness...[/bold]")
    
    path = Path("artifacts/data/restaurants.jsonl")
    if not path.exists():
        console.print("[red]Dataset missing. Run prepare-data first.[/red]")
        return
        
    table = Table(title="Evaluation Results (Groq Recommender)")
    table.add_column("Query ID")
    table.add_column("Location")
    table.add_column("Cuisines")
    table.add_column("LLM Used?")
    table.add_column("Avg Judge Score (1-5)")

    for i, query in enumerate(GOLDEN_QUERIES):
        prefs = Preferences(
            location=query["location"],
            budget=parse_budget(query["budget"]),
            cuisines=parse_cuisines(query["cuisines"]),
            min_rating=parse_min_rating(query["min_rating"]),
            free_text=query.get("free_text"),
        )
        prefs = validate_preferences(prefs)
        
        resp = recommend_with_groq(
            restaurants_jsonl=path,
            preferences=prefs,
            top_n=3,
        )
        
        scores = []
        for r in resp.top:
            score = evaluate_explanation_with_groq(query, r.explanation, r.restaurant.name)
            scores.append(score)
            
        avg_score = sum(scores) / len(scores) if scores else 0
        
        table.add_row(
            str(i+1), 
            query["location"], 
            query["cuisines"], 
            "Yes" if resp.used_llm else "No", 
            f"{avg_score:.1f}"
        )
        
    console.print(table)
    console.print("\n[dim]Check artifacts/metrics.jsonl for detailed observability logs.[/dim]")

if __name__ == "__main__":
    run_eval()
