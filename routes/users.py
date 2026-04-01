from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from database.connection import get_session
from models.users import User, UserCreate, UserSignIn, UserUpdate
from models.events import Event
from models.ai_models import EventRecommendation, MatchNotification

user_router = APIRouter(tags=["Users"])



@user_router.post("/api/register", response_model=dict)
async def register(
    user_data: UserCreate, 
    session: Session = Depends(get_session)
):
    """Register a new user"""
    # Check if username already exists
    existing = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username already exists"
        )
    
    # Limit preferences to 5 in each category
    limited_prefs = {}
    for category in ["food", "books", "movies"]:
        prefs = user_data.preferences.get(category, [])
        limited_prefs[category] = prefs[:5] if len(prefs) > 5 else prefs
    
    # Check if this is the administrator
    is_admin = (user_data.username.lower() == "administrator")
    
    # Create user
    new_user = User(
        username=user_data.username,
        age=user_data.age,
        password=user_data.password,
        preferences=limited_prefs,
        is_admin=is_admin
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "username": new_user.username,
        "is_admin": new_user.is_admin
    }

@user_router.post("/api/login", response_model=dict)
async def login(
    credentials: UserSignIn, 
    session: Session = Depends(get_session)
):
    """Login user"""
    # Find user
    user = session.exec(
        select(User).where(User.username == credentials.username)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.password != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "preferences": user.preferences
    }

@user_router.get("/api/users", response_model=List[User])
async def get_all_users(session: Session = Depends(get_session)):
    """Get all users (without passwords)"""
    users = session.exec(select(User)).all()
    # Hide passwords in response
    for user in users:
        user.password = "[HIDDEN]"
    return users

@user_router.get("/api/users/{username}", response_model=User)
async def get_user(
    username: str, 
    session: Session = Depends(get_session)
):
    """Get user by username"""
    user = session.exec(
        select(User).where(User.username == username)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hide password
    user.password = "[HIDDEN]"
    return user

@user_router.get("/api/users/id/{user_id}", response_model=User)
async def get_user_by_id(
    user_id: int,
    session: Session = Depends(get_session)
):
    """Get user by ID"""
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hide password
    user.password = "[HIDDEN]"
    return user

@user_router.delete("/api/users/{username}", response_model=dict)
async def delete_user(
    username: str, 
    session: Session = Depends(get_session)
):
    """Delete user (admin only in real implementation)"""
    if username.lower() == "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete administrator"
        )
    
    user = session.exec(
        select(User).where(User.username == username)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    session.delete(user)
    session.commit()
    
    return {"message": f"User {username} deleted successfully"}

@user_router.post("/api/clear-db", response_model=dict)
async def clear_database(session: Session = Depends(get_session)):
    """Clear all users except administrator"""
    users = session.exec(
        select(User).where(User.is_admin == False)
    ).all()
    
    for user in users:
        session.delete(user)
    
    session.commit()
    
    return {"message": "Database cleared successfully"}



class EventRecommendationCreate(BaseModel):
    user_id: int
    event_id: int
    explanation: str

@user_router.post("/api/admin/events/recommend", response_model=dict)
async def admin_create_event_recommendation(
    recommendation: EventRecommendationCreate,

    session: Session = Depends(get_session)
):
    """
    ADMIN ONLY: Create a personalized event recommendation for a user
    Temporary manual endpoint, will be replaced by AI
    """
    # Check if user exists
    user = session.get(User, recommendation.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {recommendation.user_id} not found"
        )
    
    # Check if event exists
    event = session.get(Event, recommendation.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {recommendation.event_id} not found"
        )
    
    # Create recommendation
    new_recommendation = EventRecommendation(
        user_id=recommendation.user_id,
        event_id=recommendation.event_id,
        explanation=recommendation.explanation,
        is_active=True
    )
    
    session.add(new_recommendation)
    session.commit()
    session.refresh(new_recommendation)
    
    return {
        "message": "Event recommendation created successfully",
        "recommendation_id": new_recommendation.id,
        "for_user": user.username,
        "event_title": event.title,
        "explanation": new_recommendation.explanation
    }

@user_router.get("/api/admin/events/recommendations", response_model=List[dict])
async def admin_get_all_recommendations(
    session: Session = Depends(get_session),
    limit: int = 100
):
    """
    ADMIN ONLY: Get all event recommendations
    """
    recommendations = session.exec(
        select(EventRecommendation)
        .order_by(EventRecommendation.created_at.desc())
        .limit(limit)
    ).all()
    
    result = []
    for rec in recommendations:
        user = session.get(User, rec.user_id)
        event = session.get(Event, rec.event_id)
        
        result.append({
            "id": rec.id,
            "user_id": rec.user_id,
            "username": user.username if user else "Unknown",
            "event_id": rec.event_id,
            "event_title": event.title if event else "Unknown",
            "explanation": rec.explanation,
            "created_at": rec.created_at,
            "is_active": rec.is_active,
            "was_clicked": rec.was_clicked
        })
    
    return result

@user_router.delete("/api/admin/events/recommendations/{recommendation_id}")
async def admin_delete_recommendation(
    recommendation_id: int,
    session: Session = Depends(get_session)
):
    """
    ADMIN ONLY: Delete an event recommendation
    """
    recommendation = session.get(EventRecommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    
    session.delete(recommendation)
    session.commit()
    
    return {"message": "Recommendation deleted successfully"}


class MatchNotificationCreate(BaseModel):
    user1_id: int
    user2_id: int
    match_percentage: Optional[float] = 0.0
    explanation: str

@user_router.post("/api/admin/matches/create", response_model=dict)
async def admin_create_match_notification(
    match_data: MatchNotificationCreate,
    session: Session = Depends(get_session)
):
    """
    ADMIN ONLY: Create a match notification between two users
    Temporary manual endpoint, will be replaced by AI
    """
    # Check if users exist and are different
    if match_data.user1_id == match_data.user2_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create match with the same user"
        )
    
    user1 = session.get(User, match_data.user1_id)
    user2 = session.get(User, match_data.user2_id)
    
    if not user1 or not user2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both users not found"
        )
    
    # Check if there's already an active pending match
    existing = session.exec(
        select(MatchNotification).where(
            ((MatchNotification.user1_id == match_data.user1_id) & 
             (MatchNotification.user2_id == match_data.user2_id)) |
            ((MatchNotification.user1_id == match_data.user2_id) & 
             (MatchNotification.user2_id == match_data.user1_id)),
            MatchNotification.user1_status.in_(["pending", "accepted"]),
            MatchNotification.user2_status.in_(["pending", "accepted"])
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active match notification already exists between these users"
        )
    
    # Create new match notification (expires in 7 days)
    new_match = MatchNotification(
        user1_id=match_data.user1_id,
        user2_id=match_data.user2_id,
        match_percentage=match_data.match_percentage,
        explanation=match_data.explanation,  # Сохраняем объяснение
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    
    session.add(new_match)
    session.commit()
    session.refresh(new_match)
    
    return {
        "message": "Match notification created successfully",
        "match_id": new_match.id,
        "user1": user1.username,
        "user2": user2.username,
        "match_percentage": new_match.match_percentage,
        "explanation": new_match.explanation,  # Возвращаем объяснение
        "expires_at": new_match.expires_at
    }

@user_router.get("/api/admin/matches", response_model=List[dict])
async def admin_get_all_matches(
    session: Session = Depends(get_session),
    status_filter: Optional[str] = None,
    limit: int = 100
):
    """
    ADMIN ONLY: Get all match notifications
    """
    query = select(MatchNotification).order_by(MatchNotification.created_at.desc())
    
    if status_filter:
        if status_filter == "pending":
            query = query.where(
                MatchNotification.user1_status == "pending",
                MatchNotification.user2_status == "pending"
            )
        elif status_filter == "accepted":
            query = query.where(
                (MatchNotification.user1_status == "accepted") |
                (MatchNotification.user2_status == "accepted")
            )
        elif status_filter == "completed":
            query = query.where(MatchNotification.chat_activated == True)
    
    matches = session.exec(query.limit(limit)).all()
    
    result = []
    for match in matches:
        user1 = session.get(User, match.user1_id)
        user2 = session.get(User, match.user2_id)
        
        # Determine overall status
        if match.chat_activated:
            overall_status = "chat_activated"
        elif match.user1_status == "accepted" and match.user2_status == "accepted":
            overall_status = "both_accepted"
        elif match.user1_status == "accepted" or match.user2_status == "accepted":
            overall_status = "one_accepted"
        elif match.user1_status == "rejected" or match.user2_status == "rejected":
            overall_status = "rejected"
        else:
            overall_status = "pending"
        
        result.append({
            "id": match.id,
            "user1_id": match.user1_id,
            "user1_username": user1.username if user1 else "Unknown",
            "user2_id": match.user2_id,
            "user2_username": user2.username if user2 else "Unknown",
            "match_percentage": match.match_percentage,
            "explanation": match.explanation,  # Добавлено поле
            "created_at": match.created_at,
            "expires_at": match.expires_at,
            "user1_status": match.user1_status,
            "user2_status": match.user2_status,
            "chat_activated": match.chat_activated,
            "status": overall_status
        })
    
    return result

@user_router.delete("/api/admin/matches/{match_id}")
async def admin_delete_match(
    match_id: int,
    session: Session = Depends(get_session)
):
    """
    ADMIN ONLY: Delete a match notification
    """
    match = session.get(MatchNotification, match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match notification not found"
        )
    
    session.delete(match)
    session.commit()
    
    return {"message": "Match notification deleted successfully"}


@user_router.get("/api/notifications/events/{user_id}")
async def get_user_event_recommendations(
    user_id: int,
    session: Session = Depends(get_session)
):
   
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    recommendations = session.exec(
        select(EventRecommendation)
        .where(
            EventRecommendation.user_id == user_id,
            EventRecommendation.is_active == True
        )
        .order_by(EventRecommendation.created_at.desc())
    ).all()
    
    result = []
    for rec in recommendations:
        event = session.get(Event, rec.event_id)
        if event:
            result.append({
                "recommendation_id": rec.id,
                "event_id": event.id,
                "event_title": event.title,
                "event_image": event.image,
                "event_description": event.description,
                "event_location": event.location,
                "event_tags": event.tags,
                "explanation": rec.explanation,
                "created_at": rec.created_at
            })
    
    return result

@user_router.get("/api/notifications/matches/{user_id}")
async def get_user_match_notifications(
    user_id: int,  # Добавлено
    session: Session = Depends(get_session)
):
    """
    Get all pending match notifications for a specific user
    """
    # Проверяем существование пользователя
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Find matches where this user is involved and hasn't responded yet
    matches = session.exec(
        select(MatchNotification).where(
            ((MatchNotification.user1_id == user_id) & (MatchNotification.user1_status == "pending")) |
            ((MatchNotification.user2_id == user_id) & (MatchNotification.user2_status == "pending")),
            MatchNotification.expires_at > datetime.utcnow()
        )
    ).all()
    
    result = []
    for match in matches:
        # Determine the other user
        other_user_id = match.user2_id if match.user1_id == user_id else match.user1_id
        other_user = session.get(User, other_user_id)
        
        result.append({
            "notification_id": match.id,
            "other_user_id": other_user_id,
            "other_username": other_user.username if other_user else "Unknown",
            "other_age": other_user.age if other_user else 0,
            "match_percentage": match.match_percentage,
            "explanation": match.explanation,
            "created_at": match.created_at,
            "expires_at": match.expires_at,
            "your_status": match.user1_status if match.user1_id == user_id else match.user2_status,
            "other_status": match.user2_status if match.user1_id == user_id else match.user1_status
        })
    
    return result
@user_router.get("/api/notifications/matches/{match_id}/chat/{user_id}")
async def get_match_chat_info(
    match_id: int,
    user_id: int,  # Добавлено
    session: Session = Depends(get_session)
):
    """
    Get chat information for an accepted match
    """
    match = session.get(MatchNotification, match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    # Проверяем существование пользователя
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is part of this match
    if match.user1_id != user_id and match.user2_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not part of this match"
        )
    
    # Check if chat is activated
    if not match.chat_activated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat not activated yet. Both users need to accept first."
        )
    
    # Get other user info
    other_user_id = match.user2_id if match.user1_id == user_id else match.user1_id
    other_user = session.get(User, other_user_id)
    
    return {
        "match_id": match.id,
        "chat_activated": True,
        "other_user": {
            "id": other_user.id,
            "username": other_user.username,
            "age": other_user.age
        },
        "match_percentage": match.match_percentage,
        "explanation": match.explanation,
        "activated_at": match.chat_activated_at
    }

class MatchResponse(BaseModel):
    status: str  # "accepted" or "rejected"

@user_router.post("/api/notifications/events/{recommendation_id}/click")
async def click_event_recommendation(
    recommendation_id: int,
    user_id: int,  # Добавлен параметр
    session: Session = Depends(get_session)
):
    """
    Track when user clicks on an event recommendation
    """
    recommendation = session.get(EventRecommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    
    # Проверяем по переданному user_id
    if recommendation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This recommendation does not belong to you"
        )
    
    recommendation.was_clicked = True
    recommendation.clicked_at = datetime.utcnow()
    
    session.add(recommendation)
    session.commit()
    
    return {"message": "Click tracked successfully"}

@user_router.post("/api/notifications/matches/{match_id}/respond/{user_id}")
async def respond_to_match(
    match_id: int,
    user_id: int,  # Добавлен параметр
    response: MatchResponse,
    session: Session = Depends(get_session)
):
    """
    User responds to a match notification (accept/reject)
    If both accept, chat is activated
    """
    match = session.get(MatchNotification, match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match notification not found"
        )
    
    # Проверяем существование пользователя
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is part of this match
    if match.user1_id != user_id and match.user2_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not part of this match"
        )
    
    # Check if notification is expired
    if match.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This match notification has expired"
        )
    
    # Validate response status
    if response.status not in ["accepted", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'accepted' or 'rejected'"
        )
    
    # Update user's response
    now = datetime.utcnow()
    
    if match.user1_id == user_id:
        if match.user1_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already responded to this notification"
            )
        match.user1_status = response.status
        match.user1_responded_at = now
    else:
        if match.user2_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already responded to this notification"
            )
        match.user2_status = response.status
        match.user2_responded_at = now
    
    # Check if both accepted
    chat_activated = False
    if (match.user1_status == "accepted" and match.user2_status == "accepted"):
        # Both accepted - activate chat
        match.chat_activated = True
        match.chat_activated_at = now
        chat_activated = True
    
    session.add(match)
    session.commit()
    
    # Get other user info for response
    other_user_id = match.user2_id if match.user1_id == user_id else match.user1_id
    other_user = session.get(User, other_user_id)
    
    return {
        "message": f"Match {response.status} successfully",
        "chat_activated": chat_activated,
        "other_user": {
            "id": other_user.id,
            "username": other_user.username
        } if other_user else None
    }




@user_router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow(),
        "service": "Soulmate API"
    }