from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from phase1.models import BudgetBand, Preferences, Restaurant
from phase1.preferences import cuisines_match


def _budget_band(cost_for_two: float | None) -> BudgetBand | None:
    """
    Convert numeric cost_for_two to a coarse band.

    Thresholds are pragmatic defaults and can be tuned later.
    """
    if cost_for_two is None:
        return None
    if cost_for_two <= 500:
        return BudgetBand.low
    if cost_for_two <= 1000:
        return BudgetBand.medium
    return BudgetBand.high


def _location_match(restaurant_location: str | None, requested: str | None) -> bool:
    if requested is None:
        return True
    if restaurant_location is None:
        return False
    return restaurant_location.casefold().strip() == requested.casefold().strip()


def _rating_ok(rating: float | None, min_rating: float | None) -> bool:
    if min_rating is None:
        return True
    if rating is None:
        return False
    return rating >= min_rating


def _budget_ok(cost_for_two: float | None, budget: BudgetBand | None) -> bool:
    if budget is None:
        return True
    return _budget_band(cost_for_two) == budget


def filter_hard_constraints(restaurants: Iterable[Restaurant], prefs: Preferences) -> list[Restaurant]:
    out: list[Restaurant] = []
    for r in restaurants:
        if not _location_match(r.location, prefs.location):
            continue
        if not _rating_ok(r.rating, prefs.min_rating):
            continue
        if not cuisines_match(r.cuisines, prefs.cuisines):
            continue
        if not _budget_ok(r.cost_for_two, prefs.budget):
            continue
        out.append(r)
    return out


@dataclass(frozen=True)
class FallbackStep:
    name: str
    transform: Callable[[Preferences], Preferences]


def build_fallback_policy(prefs: Preferences) -> list[FallbackStep]:
    """
    Deterministic broadening order (Phase 1):
    1) relax cuisines (drop cuisine constraint)
    2) widen budget (budget -> None)
    3) relax min_rating (step down; then drop)

    Location is kept strict in Phase 1.
    """
    steps: list[FallbackStep] = []

    if prefs.cuisines:
        steps.append(
            FallbackStep(
                name="relax_cuisines",
                transform=lambda p: Preferences(
                    location=p.location,
                    budget=p.budget,
                    cuisines=[],
                    min_rating=p.min_rating,
                    free_text=p.free_text,
                ),
            )
        )

    if prefs.budget is not None:
        steps.append(
            FallbackStep(
                name="relax_budget",
                transform=lambda p: Preferences(
                    location=p.location,
                    budget=None,
                    cuisines=p.cuisines,
                    min_rating=p.min_rating,
                    free_text=p.free_text,
                ),
            )
        )

    if prefs.min_rating is not None:
        # Step down by 0.5 twice; then drop entirely.
        def step_down(p: Preferences, new_min: float | None) -> Preferences:
            return Preferences(
                location=p.location,
                budget=p.budget,
                cuisines=p.cuisines,
                min_rating=new_min,
                free_text=p.free_text,
            )

        r = prefs.min_rating
        steps.append(FallbackStep(name="relax_min_rating_-0.5", transform=lambda p, nm=max(0.0, r - 0.5): step_down(p, nm)))
        steps.append(FallbackStep(name="relax_min_rating_-1.0", transform=lambda p, nm=max(0.0, r - 1.0): step_down(p, nm)))
        steps.append(FallbackStep(name="drop_min_rating", transform=lambda p: step_down(p, None)))

    return steps


def generate_candidates(
    *,
    restaurants: list[Restaurant],
    prefs: Preferences,
    min_candidates: int = 20,
) -> tuple[list[Restaurant], list[str], Preferences]:
    """
    Apply hard constraints and, if needed, deterministic fallback broadening.

    Returns:
    - candidates
    - relaxations_applied (names)
    - final_prefs (after relaxations)
    """
    relaxations: list[str] = []
    current = prefs

    candidates = filter_hard_constraints(restaurants, current)
    if len(candidates) >= min_candidates or len(candidates) > 0:
        return candidates, relaxations, current

    for step in build_fallback_policy(current):
        current = step.transform(current)
        relaxations.append(step.name)
        candidates = filter_hard_constraints(restaurants, current)
        if len(candidates) >= min_candidates or len(candidates) > 0:
            return candidates, relaxations, current

    return candidates, relaxations, current

