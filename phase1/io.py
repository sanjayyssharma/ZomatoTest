from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from phase1.models import Restaurant


def iter_restaurants_jsonl(path: Path) -> Iterator[Restaurant]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield Restaurant.from_json_dict(json.loads(line))


def load_restaurants(path: Path) -> list[Restaurant]:
    # De-duplicate deterministically by restaurant_id to avoid repeated entries
    # in downstream ranking/output when the artifact contains duplicates.
    out: list[Restaurant] = []
    seen: set[str] = set()
    for r in iter_restaurants_jsonl(path):
        if not r.restaurant_id or r.restaurant_id in seen:
            continue
        seen.add(r.restaurant_id)
        out.append(r)
    return out

