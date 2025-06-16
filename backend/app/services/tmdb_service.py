import httpx
import asyncio
import os
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TMDBService:
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY")
        self.base_url = "https://api.themoviedb.org/3"
        self.session = httpx.AsyncClient(timeout=30.0)
    
    async def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search for a movie by title and optional year"""
        if not self.api_key:
            logger.warning("TMDB API key not configured")
            return None
        
        params = {
            "api_key": self.api_key,
            "query": title,
            "include_adult": False
        }
        
        if year:
            params["year"] = year
        
        try:
            response = await self.session.get(f"{self.base_url}/search/movie", params=params)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if results:
                return results[0]  # Return first match
            
            return None
            
        except Exception as e:
            logger.error(f"TMDB search error for '{title}': {str(e)}")
            return None
    
    async def get_movie_details(self, tmdb_id: int) -> Optional[Dict]:
        """Get full movie details including cast and crew"""
        if not self.api_key:
            return None
        
        try:
            # Get movie details with credits
            response = await self.session.get(
                f"{self.base_url}/movie/{tmdb_id}",
                params={
                    "api_key": self.api_key,
                    "append_to_response": "credits"
                }
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"TMDB details error for ID {tmdb_id}: {str(e)}")
            return None
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()