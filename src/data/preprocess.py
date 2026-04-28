from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.data.dataset_loader import load_raw_dataset
from src.data.models import Restaurant


_CURRENCY_RE = re.compile(r"[₹$,]")
_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")
_NUM_RE = re.compile(r"(\d+(?:\.\d+)?)")


def _norm_str(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _norm_location(v: Any) -> str:
    s = _norm_str(v)
    if not s:
        return ""
    # Common normalization; can be expanded later.
    mapping = {
        "bengaluru": "bangalore",
    }
    k = s.casefold()
    return mapping.get(k, s)


def _parse_rating(v: Any) -> float | None:
    if v is None:
        return None
    s = _norm_str(v)
    if not s:
        return None
    # Handle common tokens like "NEW", "—"
    if s.casefold() in {"new", "none", "na", "n/a", "-", "—"}:
        return None
    # Handle "3/5"
    if "/" in s:
        left = s.split("/", 1)[0].strip()
        m = _NUM_RE.search(left)
        return float(m.group(1)) if m else None
    m = _NUM_RE.search(s)
    return float(m.group(1)) if m else None


def _parse_cost(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)) and pd.notna(v):
        return float(v)
    s = _norm_str(v)
    if not s:
        return None
    s = _CURRENCY_RE.sub("", s)
    s = s.replace("for two", "").replace("for 2", "").strip()
    m = _RANGE_RE.search(s)
    if m:
        lo = float(m.group(1))
        hi = float(m.group(2))
        return (lo + hi) / 2.0
    m = _NUM_RE.search(s)
    return float(m.group(1)) if m else None


def _parse_cuisines(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        items = v
    else:
        s = _norm_str(v)
        if not s:
            return []
        # Split on commas and pipes.
        items = re.split(r"[,\|/]", s)
    out: list[str] = []
    for it in items:
        t = _norm_str(it)
        if not t:
            continue
        out.append(t.lower())
    # stable de-dup preserving order
    seen: set[str] = set()
    dedup: list[str] = []
    for c in out:
        if c in seen:
            continue
        seen.add(c)
        dedup.append(c)
    return dedup


def _stable_restaurant_id(*, name: str, location: str, cuisines: Iterable[str], cost_for_two: float | None) -> str:
    key = {
        "name": name.casefold().strip(),
        "location": location.casefold().strip(),
        "cuisines": list(cuisines),
        "cost_for_two": None if cost_for_two is None else round(float(cost_for_two), 2),
    }
    payload = json.dumps(key, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _pick_first_existing(row: dict[str, Any], candidates: list[str]) -> Any:
    for c in candidates:
        if c in row and row[c] is not None:
            return row[c]
    return None


def preprocess_to_restaurants(records: list[dict[str, Any]]) -> tuple[list[Restaurant], dict[str, Any]]:
    """
    Convert raw HF records into normalized Restaurant objects + a preprocess report.

    Note: The HF dataset columns can vary; we defensively try multiple column names.
    """
    dropped_missing_name = 0
    missing_location = 0
    missing_rating = 0
    missing_cost = 0

    restaurants: list[Restaurant] = []
    for row in records:
        name_raw = _pick_first_existing(row, ["name", "restaurant_name", "Restaurant Name", "res_name", "Title"])
        name = _norm_str(name_raw)
        if not name:
            dropped_missing_name += 1
            continue

        location_raw = _pick_first_existing(row, ["location", "city", "City", "Locality", "area", "Area"])
        location = _norm_location(location_raw)
        if not location:
            missing_location += 1

        cuisines_raw = _pick_first_existing(row, ["cuisine", "cuisines", "Cuisine", "Cuisines"])
        cuisines = _parse_cuisines(cuisines_raw)

        rating_raw = _pick_first_existing(row, ["rate", "rating", "Rating", "aggregate_rating", "Aggregate rating"])
        rating = _parse_rating(rating_raw)
        if rating is None:
            missing_rating += 1

        cost_raw = _pick_first_existing(
            row,
            [
                "approx_cost(for two people)",
                "cost_for_two",
                "average_cost_for_two",
                "Average Cost for two",
                "cost",
                "Cost",
            ],
        )
        cost_for_two = _parse_cost(cost_raw)
        if cost_for_two is None:
            missing_cost += 1

        rid = _stable_restaurant_id(
            name=name,
            location=location,
            cuisines=cuisines,
            cost_for_two=cost_for_two,
        )

        restaurants.append(
            Restaurant(
                restaurant_id=rid,
                name=name,
                location=location or None,
                cuisines=cuisines,
                rating=rating,
                cost_for_two=cost_for_two,
                raw={
                    "name_source": name_raw,
                    "location_source": location_raw,
                    "cuisines_source": cuisines_raw,
                    "rating_source": rating_raw,
                    "cost_source": cost_raw,
                },
            )
        )

    # deterministic ordering
    restaurants.sort(key=lambda r: (r.location or "", r.name, r.restaurant_id))

    report = {
        "counts": {
            "input_rows": len(records),
            "output_rows": len(restaurants),
            "dropped_missing_name": dropped_missing_name,
            "missing_location": missing_location,
            "missing_rating": missing_rating,
            "missing_cost": missing_cost,
        }
    }
    return restaurants, report


def prepare_dataset_artifacts(
    *,
    dataset_name: str,
    dataset_split: str,
    hf_cache_dir: Path,
    output_dir: Path,
    allow_download: bool,
) -> dict[str, Any]:
    """
    Phase 0 entrypoint: load dataset, preprocess, and write artifacts.
    """
    dataset = load_raw_dataset(
        dataset_name=dataset_name,
        split=dataset_split,
        hf_cache_dir=hf_cache_dir,
        allow_download=allow_download,
    )

    # Convert to list[dict] early so we can compute counts deterministically.
    records = [dict(r) for r in dataset]
    restaurants, report = preprocess_to_restaurants(records)

    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    restaurants_path = data_dir / "restaurants.jsonl"
    report_path = data_dir / "preprocess_report.json"

    with restaurants_path.open("w", encoding="utf-8") as f:
        for r in restaurants:
            f.write(json.dumps(r.to_json_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True))
            f.write("\n")

    summary = {
        "dataset_name": dataset_name,
        "dataset_split": dataset_split,
        **report["counts"],
    }

    full_report = {
        "summary": summary,
        "counts": report["counts"],
        "notes": {
            "determinism": "Output is sorted by (location, name, restaurant_id). IDs are stable hashes of normalized fields.",
            "grounding": "LLM not used in Phase 0. Artifacts are intended as the single source of truth for later phases.",
        },
    }

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)

    return {
        "restaurants_jsonl_path": str(restaurants_path),
        "preprocess_report_path": str(report_path),
        "summary": summary,
    }

