# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv

from .database import init_db
from .routers import health, ingestion, stats

# Load environment variables
load_dotenv()

# Set up logging to see debug messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting up Letterboxd Wrapped Lite...")
    await init_db()
    yield
    # Shutdown
    print("⏹️  Shutting down...")

app = FastAPI(
    title="Letterboxd Wrapped Lite",
    description="Privacy-focused Letterboxd year-in-review analytics",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(ingestion.router, prefix="/api/ingest", tags=["ingestion"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])

@app.get("/")
async def root():
    tmdb_key = os.getenv("TMDB_API_KEY", "")
    return {
        "message": "Letterboxd Wrapped Lite API",
        "status": "running",
        "tmdb_configured": bool(tmdb_key and tmdb_key != "your_tmdb_api_key_here")
    }

# Keep the old endpoints for now
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/test-rss/{username}")
async def test_rss(username: str):
    """Test RSS ingestion for a user"""
    from .services.rss_ingestion import RSSIngestionService, LetterboxdRSSError
    
    service = RSSIngestionService()
    try:
        entries = await service.fetch_user_diary(username)
        return {
            "success": True,
            "username": username,
            "entries_found": len(entries),
            "sample_entries": entries[:3]  # Show first 3 entries
        }
    except LetterboxdRSSError as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        await service.close()

@app.get("/debug-rss/{username}")
async def debug_rss(username: str):
    """Debug RSS feed content"""
    import httpx
    import xml.etree.ElementTree as ET
    
    rss_url = f"https://letterboxd.com/{username}/rss/"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(rss_url)
            response.raise_for_status()
            
            content = response.text
            
            # Parse XML to check structure
            root = ET.fromstring(content)
            items = root.findall(".//item")
            
            # Get first item details if any
            first_item_details = None
            if items:
                first_item = items[0]
                first_item_details = {}
                for child in first_item:
                    first_item_details[child.tag] = child.text[:200] if child.text else None
            
            return {
                "rss_url": rss_url,
                "content_length": len(content),
                "items_found": len(items),
                "first_item": first_item_details,
                "raw_content_sample": content[:1000]  # First 1000 chars
            }
            
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug-parse/{username}")
async def debug_parse(username: str):
    """Debug individual item parsing"""
    import httpx
    import xml.etree.ElementTree as ET
    from .services.rss_ingestion import RSSIngestionService
    
    rss_url = f"https://letterboxd.com/{username}/rss/"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(rss_url)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            items = root.findall(".//item")
            
            if not items:
                return {"error": "No items found"}
            
            # Try to parse the first item manually
            first_item = items[0]
            service = RSSIngestionService()
            
            try:
                parsed_entry = service._parse_rss_item(first_item)
                return {
                    "total_items": len(items),
                    "first_item_raw": {child.tag: child.text for child in first_item},
                    "parsed_entry": parsed_entry
                }
            except Exception as e:
                return {
                    "total_items": len(items),
                    "parse_error": str(e),
                    "first_item_raw": {child.tag: child.text for child in first_item}
                }
            
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def root():
    tmdb_key = os.getenv("TMDB_API_KEY", "")
    return {
        "message": "Letterboxd Wrapped Lite API",
        "status": "running",
        "tmdb_configured": bool(tmdb_key and tmdb_key != "your_tmdb_api_key_here")
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/test-rss/{username}")
async def test_rss(username: str):
    """Test RSS ingestion for a user"""
    from .services.rss_ingestion import RSSIngestionService, LetterboxdRSSError
    
    service = RSSIngestionService()
    try:
        entries = await service.fetch_user_diary(username)
        return {
            "success": True,
            "username": username,
            "entries_found": len(entries),
            "sample_entries": entries[:3]  # Show first 3 entries
        }
    except LetterboxdRSSError as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        await service.close()

@app.get("/debug-parse/{username}")
async def debug_parse(username: str):
    """Debug individual item parsing"""
    import httpx
    import xml.etree.ElementTree as ET
    from .services.rss_ingestion import RSSIngestionService
    
    rss_url = f"https://letterboxd.com/{username}/rss/"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(rss_url)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            items = root.findall(".//item")
            
            if not items:
                return {"error": "No items found"}
            
            # Try to parse the first item manually
            first_item = items[0]
            service = RSSIngestionService()
            
            try:
                parsed_entry = service._parse_rss_item(first_item)
                return {
                    "total_items": len(items),
                    "first_item_raw": {child.tag: child.text for child in first_item},
                    "parsed_entry": parsed_entry
                }
            except Exception as e:
                return {
                    "total_items": len(items),
                    "parse_error": str(e),
                    "first_item_raw": {child.tag: child.text for child in first_item}
                }
            
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug-rss/{username}")
async def debug_rss(username: str):
    """Debug RSS feed content"""
    import httpx
    import xml.etree.ElementTree as ET
    
    rss_url = f"https://letterboxd.com/{username}/rss/"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(rss_url)
            response.raise_for_status()
            
            content = response.text
            
            # Parse XML to check structure
            root = ET.fromstring(content)
            items = root.findall(".//item")
            
            # Get first item details if any
            first_item_details = None
            if items:
                first_item = items[0]
                first_item_details = {}
                for child in first_item:
                    first_item_details[child.tag] = child.text[:200] if child.text else None
            
            return {
                "rss_url": rss_url,
                "content_length": len(content),
                "items_found": len(items),
                "first_item": first_item_details,
                "raw_content_sample": content[:1000]  # First 1000 chars
            }
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)