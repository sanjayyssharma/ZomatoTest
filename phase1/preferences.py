from __future__ import annotations

import re
from dataclasses import replace
from typing import Iterable

from phase1.models import BudgetBand, Preferences


_WS_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    s = s.strip()
    s = _WS_RE.sub(" ", s)
    return s


def _norm_token(s: str) -> str:
    return _norm(s).casefold()


def parse_budget(value: str | None) -> BudgetBand | None:
    if value is None:
        return None
    v = _norm_token(value)
    if not v:
        return None
    if v in {"low", "l", "cheap", "budget"}:
        return BudgetBand.low
    if v in {"medium", "mid", "m", "moderate"}:
        return BudgetBand.medium
    if v in {"high", "h", "expensive", "premium"}:
        return BudgetBand.high
    raise ValueError("budget must be one of: low | medium | high")


def parse_cuisines(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[,\|/]", value)
    out: list[str] = []
    for p in parts:
        t = _norm_token(p)
        if not t:
            continue
        out.append(t)
    # stable de-dup
    seen: set[str] = set()
    dedup: list[str] = []
    for c in out:
        if c in seen:
            continue
        seen.add(c)
        dedup.append(c)
    return dedup


def parse_min_rating(value: str | None) -> float | None:
    if value is None:
        return None
    v = _norm(value)
    if not v:
        return None
    try:
        r = float(v)
    except ValueError as e:
        raise ValueError("min_rating must be a number") from e
    if r < 0 or r > 5:
        raise ValueError("min_rating must be between 0 and 5")
    return r


def normalize_location(value: str | None) -> str | None:
    if value is None:
        return None
    v = _norm(value)
    if not v:
        return None
    mapping = {"bengaluru": "bangalore"}
    k = v.casefold()
    return mapping.get(k, v)


def validate_preferences(p: Preferences) -> Preferences:
    # Basic semantic validation only (Phase 1); UI can do richer validation later.
    loc = normalize_location(p.location)
    cuisines = [c.casefold().strip() for c in p.cuisines if c and c.strip()]
    cuisines = parse_cuisines(",".join(cuisines))  # de-dup + normalize
    min_rating = p.min_rating
    if min_rating is not None and (min_rating < 0 or min_rating > 5):
        raise ValueError("min_rating must be between 0 and 5")

    free_text = _norm(p.free_text) if p.free_text else None
    if free_text == "":
        free_text = None

    return replace(p, location=loc, cuisines=cuisines, free_text=free_text)


def pretty_preferences(p: Preferences) -> dict[str, object]:
    return {
        "location": p.location,
        "budget": None if p.budget is None else p.budget.value,
        "cuisines": list(p.cuisines),
        "min_rating": p.min_rating,
        "free_text": p.free_text,
    }


def cuisines_match(restaurant_cuisines: Iterable[str], required: list[str]) -> bool:
    if not required:
        return True
    rset = {c.casefold().strip() for c in restaurant_cuisines if c}
    return any(c in rset for c in required)

