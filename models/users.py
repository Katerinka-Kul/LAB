from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Optional

class UserPreferences(BaseModel):
    food: List[str] = []
    books: List[str] = []
    movies: List[str] = []

class User(BaseModel):
    username: str
    age: int
    password: str
    preferences: UserPreferences

class UserSignIn(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "user123",
                "password": "password123"
            }
        }
    )
