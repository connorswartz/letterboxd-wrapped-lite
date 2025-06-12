# app/database.py
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./letterboxd_wrapped.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

async def init_db():
    """Initialize database tables"""
    # Import models to ensure they're registered
    from .models import ProcessingSession, DiaryEntry, MovieDetails, UserStats
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    print("✅ Database tables created successfully")

def get_session() -> Generator[Session, None, None]:
    """Get database session"""
    with Session(engine) as session:
        yield session

# Convenience function for async operations
async def get_async_session():
    """Get database session for async operations"""
    return Session(engine)