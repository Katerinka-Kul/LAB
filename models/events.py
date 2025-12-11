from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, List

class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    image: str
    description: str
    location: str
    tags: List[str] = Field(sa_column=Column(JSON))
    participants: List[str] = Field(default=[], sa_column=Column(JSON))
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "title": "Italian Cuisine Evening",
                "image": "/static/images/italian-food.jpg",
                "description": "Let's cook pasta and pizza together!",
                "location": "Culinary Studio 'Tasty'",
                "tags": ["cooking", "italian cuisine", "pasta", "pizza"],
                "participants": ["user1", "user2"]
            }
        }

class EventUpdate(SQLModel):
    title: Optional[str]
    image: Optional[str]
    description: Optional[str]
    location: Optional[str]
    tags: Optional[List[str]]
    participants: Optional[List[str]]
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Updated Italian Cuisine Evening",
                "tags": ["cooking", "food"],
                "participants": ["user1", "user2", "user3"]
            }
        }