from typing import List, Dict, Optional
from sqlmodel import Session, select
from ..models import DiaryEntry, MovieDetails
import json
import logging

logger = logging.getLogger(__name__)

class StatsService:
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def compute_user_stats(self, entries: List[DiaryEntry]) -> Dict:
        """Compute all statistics for a list of diary entries"""
        total_films = len(entries)
        rated_entries = [e for e in entries if e.rating is not None]
        average_rating = sum(e.rating for e in rated_entries) / len(rated_entries) if rated_entries else None
        
        # Get enriched entries (ones with TMDB data)
        enriched_entries = [e for e in entries if e.tmdb_enriched and e.tmdb_id and hasattr(e, 'movie_details') and e.movie_details]
        
        logger.info(f"Total entries: {len(entries)}, Enriched entries: {len(enriched_entries)}")
        
        # Compute real top genres and directors from TMDB data
        top_genres = self._get_top_genres(enriched_entries)
        top_directors = self._get_top_directors(enriched_entries)
        
        # Compute top years
        years = [e.year for e in entries if e.year is not None]
        top_years = list(set(years))[:5]
        
        # TODO: Calculate total hours from TMDB runtime data
        total_hours = 0.0
        
        logger.info(f"Stats computed: {total_films} films, {len(enriched_entries)} enriched, {len(top_genres)} genres, {len(top_directors)} directors")
        
        return {
            "total_films": total_films,
            "total_hours": total_hours,
            "average_rating": average_rating,
            "top_genres": top_genres,
            "top_directors": top_directors,
            "enrichment_rate": len(enriched_entries) / total_films if total_films > 0 else 0
        }
    
    def _get_top_genres(self, enriched_entries: List[DiaryEntry]) -> List[str]:
        """Extract top genres from TMDB-enriched entries"""
        genre_counts = {}
        
        for entry in enriched_entries:
            if entry.movie_details and entry.movie_details.genres:
                try:
                    # Parse genre IDs JSON from MovieDetails
                    genre_ids = json.loads(entry.movie_details.genres) if entry.movie_details.genres else []
                    
                    # Convert TMDB genre IDs to names
                    genre_names = self._convert_genre_ids_to_names(genre_ids)
                    
                    for genre_name in genre_names:
                        if genre_name:
                            genre_counts[genre_name] = genre_counts.get(genre_name, 0) + 1
                            
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Error parsing genres for entry: {e}")
                    continue
        
        # Sort by count and return top 5
        sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
        return [genre for genre, count in sorted_genres[:5]]
    
    def _get_top_directors(self, enriched_entries: List[DiaryEntry]) -> List[str]:
        """Extract top directors from TMDB-enriched entries"""
        director_counts = {}
        
        for entry in enriched_entries:
            if entry.movie_details and entry.movie_details.director:
                director = entry.movie_details.director
                director_counts[director] = director_counts.get(director, 0) + 1
        
        # Sort by count and return top 5
        sorted_directors = sorted(director_counts.items(), key=lambda x: x[1], reverse=True)
        return [director for director, count in sorted_directors[:5]]
    
    def _convert_genre_ids_to_names(self, genre_ids: List[int]) -> List[str]:
        """Convert TMDB genre IDs to human-readable names"""
        # TMDB genre mapping
        genre_map = {
            28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
            99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
            27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
            10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
        }
        
        return [genre_map.get(genre_id, f"Genre_{genre_id}") for genre_id in genre_ids if isinstance(genre_id, int)]