from __future__ import annotations
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from phase1.models import Preferences
from phase1.preferences import parse_budget, parse_cuisines, parse_min_rating, validate_preferences
from phase2.recommender import recommend

app = FastAPI(title="AI Restaurant Recommender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecommendRequest(BaseModel):
    location: Optional[str] = None
    budget: Optional[str] = None
    cuisines: Optional[str] = None
    min_rating: Optional[str] = None
    free_text: Optional[str] = None


@app.post("/api/recommend")
def get_recommendations(req: RecommendRequest) -> dict:
    try:
        prefs = Preferences(
            location=req.location,
            budget=parse_budget(req.budget),
            cuisines=parse_cuisines(req.cuisines),
            min_rating=parse_min_rating(req.min_rating),
            free_text=req.free_text,
        )
        prefs = validate_preferences(prefs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    restaurants_file = Path("artifacts/data/restaurants.jsonl")
    if not restaurants_file.exists():
        raise HTTPException(status_code=500, detail="Restaurants artifact missing. Run prepare-data first.")

    try:
        resp = recommend(
            restaurants_jsonl=restaurants_file,
            preferences=prefs,
            top_n=10,
            min_candidates=20,
        )
        return resp.to_json_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
