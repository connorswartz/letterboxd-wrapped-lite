# backend/app/models.py
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, date
from typing import Optional, List
from enum import Enum

class SessionStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingSession(SQLModel, table=True):
    """Session tracking for user data processing"""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True)
    username: str
    status: SessionStatus = SessionStatus.PROCESSING
    progress: int = 0  # 0-100
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Relationships
    diary_entries: List["DiaryEntry"] = Relationship(back_populates="session")

class DiaryEntry(SQLModel, table=True):
    """Raw diary entry from Letterboxd"""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="processingsession.session_id", index=True)
    
    # Letterboxd data
    title: str
    year: Optional[int] = None
    rating: Optional[float] = None  # 0.5 to 5.0
    watched_date: date
    review_text: Optional[str] = None
    is_rewatch: bool = False
    
    # TMDB enrichement
    tmdb_id: Optional[int] = Field(default=None, foreign_key="moviedetails.tmdb_id")
    tmdb_enriched: bool = False
    tmdb_failed: bool = False
    
    # Relationships
    session: Optional[ProcessingSession] = Relationship(back_populates="diary_entries")
    movie_details: Optional["MovieDetails"] = Relationship(back_populates="diary_entries")

class MovieDetails(SQLModel, table=True):
    """Cached TMDB movie details"""
    tmdb_id: int = Field(primary_key=True)
    title: str
    year: int
    runtime_minutes: Optional[int] = None
    genres: str  # JSON string of genre names
    director: Optional[str] = None
    top_cast: str  # JSON string of top 5 cast members
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    
    # Cache metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    diary_entries: List[DiaryEntry] = Relationship(back_populates="movie_details")

class UserStats(SQLModel, table=True):
    """Computed statistics for a session"""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="processingsession.session_id", unique=True)
    
    # Basic stats
    total_films: int
    total_hours: float
    average_rating: Optional[float] = None
    rating_distribution: str  # JSON
    
    # Top lists (JSON strings)
    top_genres: str
    top_directors: str
    top_actors: str
    top_years: str
    
    # Viewing patterns
    viewing_streaks: str  # JSON
    monthly_distribution: str  # JSON
    seasonal_patterns: str  # JSON
    
    # Computed timestamps
    first_watch_date: Optional[date] = None
    last_watch_date: Optional[date] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Pydantic models for API responses
class SessionResponse(SQLModel):
    session_id: str
    status: SessionStatus
    progress: int
    error_message: Optional[str] = None

class StatsResponse(SQLModel):
    session_id: str
    total_films: int
    total_hours: float
    average_rating: Optional[float] = None
    top_genres: List[str]
    top_directors: List[str]
    # Add more fields as needed