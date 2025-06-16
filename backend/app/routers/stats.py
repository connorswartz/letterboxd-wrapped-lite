from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from ..models import StatsResponse, ProcessingSession, DiaryEntry, MovieDetails, SessionStatus
from ..database import get_session
from ..services.stats_service import StatsService

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
    
    # Get diary entries for this session WITH movie details relationship loaded
    entries = db.query(DiaryEntry).filter(
        DiaryEntry.session_id == session_id
    ).all()
    
    # Manually load movie details for enriched entries
    for entry in entries:
        if entry.tmdb_id:
            entry.movie_details = db.query(MovieDetails).filter(
                MovieDetails.tmdb_id == entry.tmdb_id
            ).first()
    
    if not entries:
        raise HTTPException(status_code=404, detail="No diary entries found")
    
    # Compute statistics using service with database session
    stats_service = StatsService(db)
    computed_stats = stats_service.compute_user_stats(entries)
    
    return StatsResponse(
        session_id=session_id,
        **computed_stats
    )

@router.get("/{session_id}/card")
async def generate_share_card(session_id: str):
    """Generate shareable image card"""
    # TODO: Implement card generation with @vercel/og
    return {"message": "Card generation - TODO", "session_id": session_id}