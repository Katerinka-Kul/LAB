from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from database.connection import get_session
from models.users import User, UserCreate, UserSignIn, UserUpdate

user_router = APIRouter(tags=["Users"])

@user_router.post("/api/register", response_model=dict)
async def register(
    user_data: UserCreate, 
    session: Session = Depends(get_session)
):
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
        "username": new_user.username,
        "is_admin": new_user.is_admin
    }

@user_router.post("/api/login", response_model=dict)
async def login(
    credentials: UserSignIn, 
    session: Session = Depends(get_session)
):
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

@user_router.delete("/api/users/{username}", response_model=dict)
async def delete_user(
    username: str, 
    session: Session = Depends(get_session)
):
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