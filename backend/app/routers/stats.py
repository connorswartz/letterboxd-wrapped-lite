# app/routers/stats.py
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List

from ..models import StatsResponse, ProcessingSession, DiaryEntry, SessionStatus
from ..database import get_session

router = APIRouter()

@router.get("/{session_id}")
async def get_stats(session_id: str, db: Session = Depends(get_session)):
    """Get computed statistics for a session"""
    
    # Check if session exists and is completed
    session = db.query(ProcessingSession).filter(
        ProcessingSession.session_id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != SessionStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Session not completed. Status: {session.status}"
        )
    
    # Get diary entries for this session
    entries = db.query(DiaryEntry).filter(
        DiaryEntry.session_id == session_id
    ).all()
    
    if not entries:
        raise HTTPException(status_code=404, detail="No diary entries found")
    
    # Compute basic statistics
    total_films = len(entries)
    rated_entries = [e for e in entries if e.rating is not None]
    average_rating = sum(e.rating for e in rated_entries) / len(rated_entries) if rated_entries else None
    
    # Compute top genres, directors (simplified for now)
    years = [e.year for e in entries if e.year is not None]
    top_years = list(set(years))[:5]  # Top 5 unique years
    
    # TODO: Implement more sophisticated stats once we have TMDB enrichment
    top_genres = ["Drama", "Action"]  # Placeholder
    top_directors = ["Christopher Nolan", "Martin Scorsese"]  # Placeholder
    
    return StatsResponse(
        session_id=session_id,
        total_films=total_films,
        total_hours=0.0,  # TODO: Calculate from TMDB runtime data
        average_rating=average_rating,
        top_genres=top_genres,
        top_directors=top_directors
    )

@router.get("/{session_id}/card")
async def generate_share_card(session_id: str):
    """Generate shareable image card"""
    # TODO: Implement card generation with @vercel/og
    return {"message": "Card generation - TODO", "session_id": session_id}