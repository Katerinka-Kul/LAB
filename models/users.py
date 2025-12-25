from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, List, Dict

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, nullable=False)
    age: int = Field(ge=18, le=100, nullable=False)
    password: str = Field(nullable=False)
    is_admin: bool = Field(default=False)
    
    # Preferences stored as JSON
    preferences: Dict[str, List[str]] = Field(
        default_factory=lambda: {"food": [], "books": [], "movies": []},
        sa_column=Column(JSON)
    )

class UserCreate(SQLModel):
    username: str
    age: int
    password: str
    preferences: Dict[str, List[str]] = {
        "food": [],
        "books": [],
        "movies": []
    }

class UserSignIn(SQLModel):
    username: str
    password: str

class UserUpdate(SQLModel):
    age: Optional[int] = None
    password: Optional[str] = None
    preferences: Optional[Dict[str, List[str]]] = None