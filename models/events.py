from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, List

class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(nullable=False)
    image: str = Field(default="")
    description: str = Field(default="")
    location: str = Field(nullable=False)
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))

class EventCreate(SQLModel):
    title: str
    image: str = ""
    description: str = ""
    location: str
    tags: List[str] = []
    participants: List[str] = []

class EventUpdate(SQLModel):
    title: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None
    participants: Optional[List[str]] = None