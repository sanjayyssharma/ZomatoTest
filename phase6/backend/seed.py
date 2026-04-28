import json
from pathlib import Path
from .database import SessionLocal, engine, Base
from .models import RestaurantDB

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    path = Path("artifacts/data/restaurants.jsonl")
    if not path.exists():
        print("Data file not found. Run phase 0 first.")
        return
        
    if db.query(RestaurantDB).first():
        print("Database already seeded.")
        return
        
    print("Seeding database...")
    restaurants = []
    seen_ids = set()
    
    with open(path, "r") as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            
            rid = data["restaurant_id"]
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            
            cuisines_str = ",".join(data.get("cuisines", []))
            
            r = RestaurantDB(
                id=rid,
                name=data["name"],
                location=data.get("location", ""),
                rating=data.get("rating"),
                cost_for_two=data.get("cost_for_two"),
                cuisines=cuisines_str,
                raw_data=json.dumps(data)
            )
            restaurants.append(r)
            
            if len(restaurants) >= 1000:
                db.bulk_save_objects(restaurants)
                db.commit()
                restaurants = []
                
    if restaurants:
        db.bulk_save_objects(restaurants)
        db.commit()
        
    count = db.query(RestaurantDB).count()
    print(f"Database seeded with {count} restaurants.")
    db.close()

if __name__ == "__main__":
    seed_database()
