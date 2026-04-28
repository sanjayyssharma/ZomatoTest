from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console

from phase1.models import Preferences
from phase1.preferences import parse_budget, parse_cuisines, parse_min_rating, validate_preferences
from phase2.recommender import recommend


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="phase2", add_help=True)
    sub = p.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("recommend", help="LLM-assisted ranking + grounded explanations")
    rec.add_argument("--restaurants", type=str, default="artifacts/data/restaurants.jsonl")
    rec.add_argument("--location", type=str, default=None)
    rec.add_argument("--budget", type=str, default=None, help="low|medium|high")
    rec.add_argument("--cuisines", type=str, default=None, help="comma-separated cuisines")
    rec.add_argument("--min-rating", type=str, default=None)
    rec.add_argument("--free-text", type=str, default=None)
    rec.add_argument("--top-n", type=int, default=10)
    rec.add_argument("--min-candidates", type=int, default=20)
    rec.add_argument("--json", action="store_true", help="Output JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    console = Console()
    args = _build_parser().parse_args(argv)

    if args.command == "recommend":
        try:
            prefs = Preferences(
                location=args.location,
                budget=parse_budget(args.budget),
                cuisines=parse_cuisines(args.cuisines),
                min_rating=parse_min_rating(args.min_rating),
                free_text=args.free_text,
            )
            prefs = validate_preferences(prefs)
        except ValueError as e:
            console.print(f"[red]Invalid preferences:[/red] {e}")
            return 2

        path = Path(args.restaurants)
        if not path.exists():
            console.print(f"[red]Missing restaurants artifact:[/red] {path}")
            console.print("[dim]Run Phase 0 first: python3 -m src prepare-data[/dim]")
            return 2

        resp = recommend(
            restaurants_jsonl=path,
            preferences=prefs,
            top_n=max(1, args.top_n),
            min_candidates=max(1, args.min_candidates),
        )

        if args.json:
            console.print_json(json.dumps(resp.to_json_dict(), ensure_ascii=False))
            return 0

        console.print("[bold]Phase 2 recommendations (LLM-assisted)[/bold]")
        console.print(f"[dim]Candidates:[/dim] {resp.candidate_count} / {resp.total_restaurants} | [dim]Used LLM:[/dim] {resp.used_llm}")
        if resp.relaxations_applied:
            console.print(f"[yellow]Relaxations applied:[/yellow] {', '.join(resp.relaxations_applied)}")
        console.print()

        if not resp.top:
            console.print("[red]No matches found.[/red]")
            return 0

        for i, r in enumerate(resp.top, start=1):
            rating = "—" if r.restaurant.rating is None else f"{r.restaurant.rating:.1f}"
            cost = "—" if r.restaurant.cost_for_two is None else f"{int(r.restaurant.cost_for_two)}"
            cuisines = ", ".join(r.restaurant.cuisines[:4]) if r.restaurant.cuisines else "—"
            loc = r.restaurant.location or "—"
            console.print(f"{i}. [bold]{r.restaurant.name}[/bold]  [dim]({loc})[/dim]")
            console.print(f"   [cyan]Why?[/cyan] {r.explanation}")
            console.print(f"   [dim]rating: {rating} | cost_for_two: {cost} | cuisines: {cuisines}[/dim]")
            console.print()

        return 0

    console.print("[red]Unknown command[/red]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
