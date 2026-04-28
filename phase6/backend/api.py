import json
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from .database import get_db, Base, engine
from .models import RestaurantDB

from phase1.models import Preferences, Restaurant as Phase1Restaurant
from phase1.preferences import parse_budget, parse_cuisines, parse_min_rating, validate_preferences
from phase4.recommender import rank_with_groq
from phase4.instrumentation import log_event

Base.metadata.create_all(bind=engine)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(title="Phase 6 Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"OMG ERROR: {exc.errors()} Body: {await request.body()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


class RecommendRequest(BaseModel):
    location: Optional[str] = None
    budget: Optional[str] = None
    cuisines: Optional[str] = None
    min_rating: Optional[str] = None
    free_text: Optional[str] = None

response_cache = {}

@app.post("/api/recommend")
def get_recommendations(req: RecommendRequest, db: Session = Depends(get_db)):
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
        
    cache_key = str(prefs)
    if cache_key in response_cache:
        log_event("cache_hit", {"key": cache_key})
        return response_cache[cache_key]

    query = db.query(RestaurantDB)
    
    if prefs.location:
        query = query.filter(RestaurantDB.location.ilike(prefs.location))
        
    if prefs.min_rating is not None:
        query = query.filter(RestaurantDB.rating >= prefs.min_rating)
        
    if prefs.budget:
        if prefs.budget.value == "low":
            query = query.filter(RestaurantDB.cost_for_two <= 500)
        elif prefs.budget.value == "medium":
            query = query.filter(RestaurantDB.cost_for_two > 500, RestaurantDB.cost_for_two <= 1000)
        else:
            query = query.filter(RestaurantDB.cost_for_two > 1000)
            
    db_results = query.all()
    
    candidates = []
    req_cuisines = [c.casefold().strip() for c in prefs.cuisines if c]
    
    for row in db_results:
        data = json.loads(row.raw_data)
        restaurant = Phase1Restaurant(**data)
        
        if req_cuisines:
            res_c = [c.casefold().strip() for c in restaurant.cuisines if c]
            if not any(c in res_c for c in req_cuisines):
                continue
                
        candidates.append(restaurant)
        
    if not candidates:
        return {"top": [], "candidate_count": 0, "used_llm": False}
        
    ranked = rank_with_groq(prefs, candidates, top_k=20)
    top = ranked[:5]
    
    used_llm = bool(top and top[0].explanation != "Fallback to baseline ranker.")
    
    # Format the top response
    top_json = []
    for r in top:
        top_json.append({
            "restaurant_id": r.restaurant.restaurant_id,
            "name": r.restaurant.name,
            "location": r.restaurant.location,
            "cuisines": list(r.restaurant.cuisines),
            "rating": r.restaurant.rating,
            "cost_for_two": r.restaurant.cost_for_two,
            "explanation": r.explanation
        })
    
    resp = {
        "candidate_count": len(candidates),
        "used_llm": used_llm,
        "top": top_json
    }
    
    response_cache[cache_key] = resp
    return resp
