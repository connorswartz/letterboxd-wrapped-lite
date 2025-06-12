# app/routers/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2025-06-11T00:00:00Z"}

@router.get("/ready")
async def readiness_check():
    """Readiness check for deployment"""
    # TODO: Check database connection
    return {"status": "ready"}