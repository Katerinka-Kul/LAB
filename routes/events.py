from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, Session
from typing import List

from database.connection import get_session
from models.events import Event, EventUpdate

event_router = APIRouter(tags=["Events"])

@event_router.get("/", response_model=List[Event])
async def retrieve_all_events(session: Session = Depends(get_session)) -> List[Event]:
    statement = select(Event)
    events = session.exec(statement).all()
    return events

@event_router.get("/{id}", response_model=Event)
async def retrieve_event(id: int, session: Session = Depends(get_session)) -> Event:
    event = session.get(Event, id)
    if event:
        return event
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Event not found"
    )

@event_router.post("/new")
async def create_event(new_event: Event, session: Session = Depends(get_session)) -> dict:
    session.add(new_event)
    session.commit()
    session.refresh(new_event)
    return {
        "message": "Event created successfully"
    }

@event_router.put("/edit/{id}", response_model=Event)
async def update_event(id: int, new_data: EventUpdate, session: Session = Depends(get_session)) -> Event:
    event = session.get(Event, id)
    if event:
        event_data = new_data.dict(exclude_unset=True)
        for key, value in event_data.items():
            setattr(event, key, value)
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Event not found"
    )

@event_router.delete("/{id}")
async def delete_event(id: int, session: Session = Depends(get_session)) -> dict:
    event = session.get(Event, id)
    if event:
        session.delete(event)
        session.commit()
        return {
            "message": "Event deleted successfully"
        }
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Event not found"
    )

@event_router.post("/{id}/join")
async def join_event(id: int, body: dict, session: Session = Depends(get_session)):
    event = session.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    username = body.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required"
        )
    
    # Add user to participants if not already there
    if username not in event.participants:
        event.participants.append(username)
        session.add(event)
        session.commit()
        session.refresh(event)
        
        return {
            "message": "You have joined the event",
            "is_joined": True,
            "participants": event.participants
        }
    else:
        # User is already joined
        return {
            "message": "You are already attending this event",
            "is_joined": True,
            "participants": event.participants
        }

@event_router.post("/{id}/leave")
async def leave_event(id: int, body: dict, session: Session = Depends(get_session)):
    event = session.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    username = body.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required"
        )
    
    # Remove user from participants
    if username in event.participants:
        event.participants.remove(username)
        session.add(event)
        session.commit()
        session.refresh(event)
        
        return {
            "message": "You have left the event",
            "is_joined": False,
            "participants": event.participants
        }
    else:
        # User is not in participants
        return {
            "message": "You are not attending this event",
            "is_joined": False,
            "participants": event.participants
        }

@event_router.get("/{id}/participants")
async def get_event_participants(id: int, session: Session = Depends(get_session)):
    event = session.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event.participants