## Phase 1: Deterministic candidate generation (baseline recommender)

This folder implements Phase 1 from `docs/architecture.md` as a standalone package.

### What it does
- Validates user preferences (location, budget, cuisines, min rating, optional free-text).
- Filters restaurants deterministically using **hard constraints**.
- Applies a deterministic **fallback broadening policy** when the result set is empty/too small.
- Produces a baseline ranking with stable tie-breakers.

### Input data
Reads the Phase 0 artifact:
- `artifacts/data/restaurants.jsonl`

### Run (CLI)

```bash
python3 -m phase1 recommend --location "Banashankari" --budget medium --cuisines "north indian, chinese" --min-rating 4.0 --top-n 10
```

To output machine-readable JSON:

```bash
python3 -m phase1 recommend --location "Banashankari" --budget medium --cuisines "north indian, chinese" --min-rating 4.0 --top-n 10 --json
```

