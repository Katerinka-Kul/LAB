
from fastapi import Depends, HTTPException, status, Header
from sqlmodel import Session, select
from database.connection import get_session
from models.users import User

async def get_current_admin(
    authorization: str = Header(None),
    session: Session = Depends(get_session)
) -> User:
    """
    Dependency to get current admin user
    Expects username in Authorization header (simplified for development)
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Simplified: Authorization: "username"
    username = authorization
    
    user = session.exec(
        select(User).where(User.username == username)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return user