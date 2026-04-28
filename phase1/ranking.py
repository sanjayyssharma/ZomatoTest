from __future__ import annotations

from phase1.models import Restaurant


def rank_baseline(candidates: list[Restaurant]) -> list[Restaurant]:
    """
    Deterministic baseline ranking.

    Tie-breakers are stable to guarantee reproducibility.
    """
    def key(r: Restaurant) -> tuple:
        rating = -r.rating if r.rating is not None else float("inf")  # best first; missing last
        cost = r.cost_for_two if r.cost_for_two is not None else float("inf")  # cheaper first; missing last
        loc = (r.location or "").casefold()
        name = r.name.casefold()
        return (rating, cost, loc, name, r.restaurant_id)

    return sorted(candidates, key=key)

