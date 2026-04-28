from sqlalchemy import Column, String, Float, Integer
from .database import Base

class RestaurantDB(Base):
    __tablename__ = "restaurants"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String, index=True)
    rating = Column(Float, nullable=True)
    cost_for_two = Column(Float, nullable=True)
    cuisines = Column(String) 
    raw_data = Column(String)
