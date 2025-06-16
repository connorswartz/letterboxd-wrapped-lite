# app/routers/ingestion.py
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import uuid
from typing import Optional
from sqlmodel import Session

from ..services.rss_ingestion import RSSIngestionService, LetterboxdRSSError
from ..models import SessionResponse, SessionStatus, ProcessingSession, DiaryEntry, MovieDetails
from ..database import get_session
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/rss/{username}")
async def ingest_rss(
    username: str, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session)
) -> SessionResponse:
    """Start RSS ingestion for a Letterboxd user"""
    
    # Validate username format
    if not username.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="Invalid username format"
        )
    
    try:
        # Create processing session
        session_id = str(uuid.uuid4())
        
        # Create session record in database
        processing_session = ProcessingSession(
            session_id=session_id,
            username=username,
            status=SessionStatus.PROCESSING,
            progress=0
        )
        
        db.add(processing_session)
        db.commit()
        db.refresh(processing_session)
        
        # Add background task for processing
        background_tasks.add_task(process_rss_data, session_id, username)
        
        return SessionResponse(
            session_id=session_id,
            status=SessionStatus.PROCESSING,
            progress=0
        )
    
    except Exception as e:
        logger.error(f"Error creating RSS ingestion session: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.post("/csv")
async def ingest_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_session)
) -> SessionResponse:
    """Upload and process Letterboxd CSV export"""
    
    # Validate file type
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV"
        )
    
    # Check file size (max 10MB)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large (max 10MB)"
        )
    
    session_id = str(uuid.uuid4())
    
    try:
        # Create session record
        processing_session = ProcessingSession(
            session_id=session_id,
            username="csv_upload",
            status=SessionStatus.PROCESSING,
            progress=0
        )
        
        db.add(processing_session)
        db.commit()
        
        # Read file content
        content = await file.read()
        csv_data = content.decode('utf-8')
        
        # Add background task for processing
        background_tasks.add_task(process_csv_data, session_id, csv_data)
        
        return SessionResponse(
            session_id=session_id,
            status=SessionStatus.PROCESSING,
            progress=0
        )
        
    except UnicodeDecodeError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid CSV encoding (must be UTF-8)"
        )
    except Exception as e:
        logger.error(f"Error creating CSV ingestion session: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.get("/status/{session_id}")
async def get_ingestion_status(
    session_id: str, 
    db: Session = Depends(get_session)
) -> SessionResponse:
    """Get status of data ingestion process"""
    
    session = db.query(ProcessingSession).filter(
        ProcessingSession.session_id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        progress=session.progress,
        error_message=session.error_message
    )

# Background task functions
async def process_rss_data(session_id: str, username: str):
    """Background task to process RSS data with TMDB enrichment"""
    from sqlmodel import create_engine, Session
    from ..services.tmdb_service import TMDBService
    import os
    
    # Create a new database session for the background task
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./letterboxd_wrapped.db")
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
    
    with Session(engine) as db:
        rss_service = RSSIngestionService()
        tmdb_service = TMDBService()
        
        try:
            # Get the session
            session = db.query(ProcessingSession).filter(
                ProcessingSession.session_id == session_id
            ).first()
            
            if not session:
                logger.error(f"Session {session_id} not found")
                return
            
            session.progress = 10
            db.commit()
            
            # Fetch RSS data
            logger.info(f"Fetching RSS data for {username}")
            entries = await rss_service.fetch_user_diary(username)
            
            session.progress = 30
            db.commit()
            
            # Store entries in database with TMDB enrichment
            logger.info(f"Processing {len(entries)} entries with TMDB enrichment")
            total_entries = len(entries)
            
            for i, entry_data in enumerate(entries):
                # Create diary entry
                diary_entry = DiaryEntry(
                    session_id=session_id,
                    title=entry_data["title"],
                    year=entry_data["year"],
                    rating=entry_data["rating"],
                    watched_date=entry_data["watched_date"].date() if entry_data["watched_date"] else None,
                    review_text=entry_data["review_text"],
                    is_rewatch=entry_data["is_rewatch"]
                )
                
                # Try TMDB enrichment
                tmdb_data = await tmdb_service.search_movie(entry_data["title"], entry_data["year"])
                if tmdb_data:
                    tmdb_id = tmdb_data.get("id")
                    diary_entry.tmdb_id = tmdb_id
                    diary_entry.tmdb_enriched = True
                    
                    # Check if MovieDetails already exists
                    existing_movie = db.query(MovieDetails).filter(
                        MovieDetails.tmdb_id == tmdb_id
                    ).first()
                    
                    if not existing_movie:
                        # Create new MovieDetails record
                        movie_details = MovieDetails(
                            tmdb_id=tmdb_id,
                            title=tmdb_data.get("title", entry_data["title"]),
                            year=int(tmdb_data.get("release_date", "")[:4]) if tmdb_data.get("release_date") else entry_data["year"],
                            runtime_minutes=tmdb_data.get("runtime"),  # Will be None for search results
                            genres=json.dumps(tmdb_data.get("genre_ids", [])),  # Store as JSON
                            director=None,  # Search results don't include director
                            top_cast=json.dumps([]),  # Search results don't include cast
                            overview=tmdb_data.get("overview"),
                            poster_path=tmdb_data.get("poster_path")
                        )
                        db.add(movie_details)
                        logger.info(f"Created MovieDetails for '{entry_data['title']}' (TMDB ID: {tmdb_id})")
                    
                    logger.info(f"Enriched '{entry_data['title']}' with TMDB ID {tmdb_id}")
                else:
                    diary_entry.tmdb_failed = True
                    logger.warning(f"No TMDB match for '{entry_data['title']}' ({entry_data['year']})")
                
                db.add(diary_entry)
                
                # Update progress
                progress = 30 + int((i + 1) / total_entries * 60)  # 30-90% range
                session.progress = progress
                db.commit()
            
            # Update session status to completed
            session.status = SessionStatus.COMPLETED
            session.progress = 100
            session.completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Successfully processed {len(entries)} entries for {username}")
            
        except LetterboxdRSSError as e:
            logger.error(f"RSS error for {username}: {str(e)}")
            session = db.query(ProcessingSession).filter(
                ProcessingSession.session_id == session_id
            ).first()
            if session:
                session.status = SessionStatus.FAILED
                session.error_message = str(e)
                db.commit()
        
        except Exception as e:
            logger.error(f"Unexpected error processing {username}: {str(e)}")
            session = db.query(ProcessingSession).filter(
                ProcessingSession.session_id == session_id
            ).first()
            if session:
                session.status = SessionStatus.FAILED
                session.error_message = f"Processing error: {str(e)}"
                db.commit()
        
        finally:
            await rss_service.close()
            await tmdb_service.close()

async def process_csv_data(session_id: str, csv_data: str):
    """Background task to process CSV data"""
    # TODO: Implement CSV parsing and storage
    logger.info(f"CSV processing for session {session_id} - TODO")
    pass