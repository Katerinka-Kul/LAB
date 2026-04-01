from sqlmodel import SQLModel, Field, Index
from typing import Optional
from datetime import datetime

class EventRecommendation(SQLModel, table=True):
    """Model for event recommendations"""
    __tablename__ = "event_recommendation"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    event_id: int = Field(foreign_key="event.id", index=True)
    explanation: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    was_clicked: bool = Field(default=False)
    clicked_at: Optional[datetime] = Field(default=None)
    
    # Правильное размещение индексов
    __table_args__ = (
        Index('idx_rec_user_event', 'user_id', 'event_id'),
    )

class MatchNotification(SQLModel, table=True):
    """Model for match notifications between users"""
    __tablename__ = "match_notification"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user1_id: int = Field(foreign_key="user.id", index=True)
    user2_id: int = Field(foreign_key="user.id", index=True)
    match_percentage: float = Field(default=0.0)
    explanation: str = Field(default="", nullable=False)  # ДОБАВЛЕНО поле
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default=None)
    
    # Status fields
    user1_status: str = Field(default="pending")  # pending, accepted, rejected
    user2_status: str = Field(default="pending")
    user1_responded_at: Optional[datetime] = Field(default=None)
    user2_responded_at: Optional[datetime] = Field(default=None)
    
    # Chat activation
    chat_activated: bool = Field(default=False)
    chat_activated_at: Optional[datetime] = Field(default=None)
    
    # Правильное размещение индексов
    __table_args__ = (
        Index('idx_match_users', 'user1_id', 'user2_id'),
        Index('idx_match_status', 'user1_status', 'user2_status'),
    )