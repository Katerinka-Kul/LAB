from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from database.connection import get_session
from models.events import Event, EventCreate, EventUpdate

event_router = APIRouter(tags=["Events"])


@event_router.get("/", response_model=List[Event])
async def retrieve_all_events(session: Session = Depends(get_session)):
    """Get all events"""
    statement = select(Event)
    events = session.exec(statement).all()
    return events

@event_router.get("/{id}", response_model=Event)
async def retrieve_event(id: int, session: Session = Depends(get_session)):
    """Get event by ID"""
    event = session.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event

@event_router.post("/new")
async def create_event(new_event: EventCreate, session: Session = Depends(get_session)):
    """Create new event"""
    event = Event(**new_event.dict())
    session.add(event)
    session.commit()
    session.refresh(event)
    
    return {
        "message": "Event created successfully",
        "event_id": event.id
    }

@event_router.put("/edit/{id}", response_model=Event)
async def update_event(id: int, new_data: EventUpdate, session: Session = Depends(get_session)):
    """Update existing event"""
    event = session.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Update only provided fields
    event_data = new_data.dict(exclude_unset=True)
    for key, value in event_data.items():
        setattr(event, key, value)
    
    session.add(event)
    session.commit()
    session.refresh(event)
    
    return event

@event_router.delete("/{id}")
async def delete_event(id: int, session: Session = Depends(get_session)):
    """Delete event"""
    event = session.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    session.delete(event)
    session.commit()
    
    return {
        "message": "Event deleted successfully"
    }