import json
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from phase6.backend.database import SessionLocal
from phase6.backend.models import RestaurantDB
from phase1.models import Preferences, Restaurant as Phase1Restaurant
from phase1.preferences import parse_budget, parse_cuisines, parse_min_rating, validate_preferences
from phase4.recommender import rank_with_groq

st.set_page_config(
    page_title="LUMIÈRE | AI Recommender",
    page_icon="🍽️",
    layout="centered"
)

st.title("🍽️ LUMIÈRE")
st.markdown("### Discover Your Next Favorite Meal")
st.markdown("Let our AI culinary concierge guide you to extraordinary dining experiences tailored to your palate.")

# Sidebar / Main Form
with st.form("preferences_form"):
    st.subheader("Your Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        location = st.text_input("Location (Neighborhood/City)", value="BTM", placeholder="e.g. BTM, Indiranagar")
        budget = st.selectbox("Budget", options=["Low", "Medium", "High"], index=1)
        
    with col2:
        min_rating = st.slider("Minimum Rating", min_value=1.0, max_value=5.0, value=4.0, step=0.1)
        cuisines = st.text_input("Cravings (Optional)", placeholder="e.g. Italian, Cafe")
        
    submitted = st.form_submit_button("Get Recommendations", type="primary")

if submitted:
    with st.spinner("Discovering the best options..."):
        try:
            # 1. Parse & Validate
            prefs = Preferences(
                location=location.strip() if location else None,
                budget=parse_budget(budget),
                cuisines=parse_cuisines(cuisines) if cuisines else [],
                min_rating=parse_min_rating(str(min_rating)),
                free_text=None
            )
            prefs = validate_preferences(prefs)
            
            # 2. Query Database
            db = SessionLocal()
            try:
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
                
                # 3. Filter Candidates
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
                    st.warning("No matches found. Try broadening your search criteria.")
                else:
                    # 4. LLM Ranking
                    ranked = rank_with_groq(prefs, candidates, top_k=20)
                    top = ranked[:5]
                    
                    used_llm = bool(top and top[0].explanation != "Fallback to baseline ranker.")
                    
                    st.success(f"Found {len(candidates)} candidates! (Used LLM: {'Yes' if used_llm else 'No'})")
                    
                    # 5. Display Results
                    for r in top:
                        with st.container():
                            st.markdown(f"### {r.restaurant.name}")
                            st.markdown(f"**⭐ {r.restaurant.rating}** | 📍 {r.restaurant.location} | 💵 ₹{r.restaurant.cost_for_two} for two")
                            
                            tags = "".join([f"`{c.strip()}` " for c in r.restaurant.cuisines])
                            st.markdown(tags)
                            
                            if r.explanation:
                                st.info(f"✨ {r.explanation}")
                                
                            st.divider()

            finally:
                db.close()
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
