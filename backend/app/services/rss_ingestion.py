# app/services/rss_ingestion.py
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)

class LetterboxdRSSError(Exception):
    """Custom exception for RSS-related errors"""
    pass

class RSSIngestionService:
    def __init__(self):
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Letterboxd-Wrapped-Lite/0.1.0 (Educational Project)"
            }
        )
    
    async def fetch_user_diary(self, username: str) -> List[Dict]:
        """
        Fetch diary entries from Letterboxd RSS feed
        Returns list of diary entries with error handling
        """
        rss_url = f"https://letterboxd.com/{username}/rss/"
        
        try:
            logger.info(f"Fetching RSS feed for user: {username}")
            response = await self.session.get(rss_url)
            response.raise_for_status()
            
            # Parse RSS XML
            entries = self._parse_rss_content(response.text)
            logger.info(f"Successfully parsed {len(entries)} entries for {username}")
            
            return entries
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LetterboxdRSSError(f"User '{username}' not found on Letterboxd")
            elif e.response.status_code == 403:
                raise LetterboxdRSSError(f"User '{username}' has private diary")
            else:
                raise LetterboxdRSSError(f"HTTP error {e.response.status_code}")
                
        except httpx.TimeoutException:
            raise LetterboxdRSSError("Request timed out - Letterboxd may be slow")
            
        except ET.ParseError as e:
            raise LetterboxdRSSError(f"Invalid RSS format: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error fetching RSS for {username}: {str(e)}")
            raise LetterboxdRSSError(f"Failed to fetch diary: {str(e)}")
    
    def _parse_rss_content(self, xml_content: str) -> List[Dict]:
        """Parse RSS XML and extract diary entries"""
        try:
            root = ET.fromstring(xml_content)
            entries = []
            
            # Find all items in the RSS feed
            for item in root.findall(".//item"):
                entry = self._parse_rss_item(item)
                if entry:
                    entries.append(entry)
            
            return entries
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {str(e)}")
            raise
    
    def _parse_rss_item(self, item: ET.Element) -> Optional[Dict]:
        """Parse individual RSS item into diary entry"""
        try:
            # Extract basic fields
            title_elem = item.find("title")
            pub_date_elem = item.find("pubDate")
            
            logger.info(f"Parsing item - title_elem exists: {title_elem is not None}, pub_date_elem exists: {pub_date_elem is not None}")
            
            # Check each element individually for better debugging
            if title_elem is None:
                logger.warning("Title element is missing")
                return None
                
            if pub_date_elem is None:
                logger.warning("PubDate element is missing")
                return None
            
            title_text = title_elem.text or ""
            pub_date_text = pub_date_elem.text or ""
            
            logger.info(f"Title text: '{title_text}'")
            logger.info(f"PubDate text: '{pub_date_text}'")
            
            # Letterboxd RSS has structured data in namespaced elements
            film_title_elem = item.find("{https://letterboxd.com}filmTitle")
            film_year_elem = item.find("{https://letterboxd.com}filmYear")
            watched_date_elem = item.find("{https://letterboxd.com}watchedDate")
            rating_elem = item.find("{https://letterboxd.com}memberRating")
            rewatch_elem = item.find("{https://letterboxd.com}rewatch")
            description_elem = item.find("description")
            
            logger.info(f"Film title: {film_title_elem.text if film_title_elem is not None else 'None'}")
            logger.info(f"Film year: {film_year_elem.text if film_year_elem is not None else 'None'}")
            logger.info(f"Watched date: {watched_date_elem.text if watched_date_elem is not None else 'None'}")
            
            # Extract movie info - use structured data if available, fallback to title parsing
            if film_title_elem is not None and film_title_elem.text:
                movie_title = film_title_elem.text
                movie_year = int(film_year_elem.text) if film_year_elem is not None and film_year_elem.text else None
            else:
                # Fallback to parsing title
                movie_info = self._extract_movie_info(title_text)
                if not movie_info:
                    logger.warning(f"Could not parse movie info from title: {title_text}")
                    return None
                movie_title = movie_info["title"]
                movie_year = movie_info["year"]
            
            # Parse watched date - use structured data if available
            if watched_date_elem is not None and watched_date_elem.text:
                try:
                    watched_date = datetime.strptime(watched_date_elem.text, "%Y-%m-%d")
                    logger.info(f"Parsed watched date: {watched_date}")
                except ValueError as e:
                    logger.warning(f"Failed to parse structured watched date: {e}")
                    watched_date = self._parse_pub_date(pub_date_text)
            else:
                watched_date = self._parse_pub_date(pub_date_text)
            
            if not watched_date:
                logger.warning(f"Could not parse date: {pub_date_text}")
                return None
            
            # Extract rating - use structured data if available
            rating = None
            if rating_elem is not None and rating_elem.text:
                try:
                    rating = float(rating_elem.text)
                    logger.info(f"Parsed rating: {rating}")
                except ValueError:
                    pass
            
            if rating is None:
                # Fallback to parsing from title or description
                rating_info = self._extract_rating_info(title_text)
                rating = rating_info.get("rating")
            
            # Extract rewatch info
            is_rewatch = False
            if rewatch_elem is not None and rewatch_elem.text:
                is_rewatch = rewatch_elem.text.lower() == "yes"
                logger.info(f"Is rewatch: {is_rewatch}")
            
            # Extract review text from description
            description_text = description_elem.text or "" if description_elem is not None else ""
            review_text = self._extract_review_text(description_text)
            
            result = {
                "title": movie_title,
                "year": movie_year,
                "watched_date": watched_date,
                "rating": rating,
                "is_rewatch": is_rewatch,
                "review_text": review_text
            }
            
            logger.info(f"Successfully parsed entry: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing RSS item: {str(e)}", exc_info=True)
            return None
    
    def _extract_movie_info(self, title: str) -> Optional[Dict]:
        """Extract movie title and year from RSS title"""
        # Pattern: "Movie Title, 2023" or "Movie Title (2023)"
        patterns = [
            r"^(.+),\s*(\d{4})$",  # "Title, 2023"
            r"^(.+)\s*\((\d{4})\)$",  # "Title (2023)"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, title.strip())
            if match:
                return {
                    "title": match.group(1).strip(),
                    "year": int(match.group(2))
                }
        
        # Fallback: assume no year info
        return {"title": title.strip(), "year": None}
    
    def _extract_rating_info(self, description: str) -> Dict:
        """Extract rating and rewatch info from description HTML"""
        rating_info = {"rating": None, "is_rewatch": False}
        
        # Look for star ratings (★★★★☆ pattern)
        star_match = re.search(r"(★+)", description)
        if star_match:
            stars = len(star_match.group(1))
            rating_info["rating"] = float(stars)
        
        # Look for half stars or explicit ratings
        if "½" in description and star_match:
            rating_info["rating"] += 0.5
        
        # Check for rewatch indicator
        if "rewatch" in description.lower() or "re-watch" in description.lower():
            rating_info["is_rewatch"] = True
        
        return rating_info
    
    def _extract_review_text(self, description: str) -> Optional[str]:
        """Extract review text from description, removing HTML"""
        # Simple HTML tag removal
        clean_text = re.sub(r"<[^>]+>", "", description)
        clean_text = clean_text.strip()
        
        # Remove rating stars and common patterns
        clean_text = re.sub(r"★+[½]?", "", clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        
        return clean_text if clean_text and len(clean_text) > 10 else None
    
    def _parse_pub_date(self, pub_date_str: str) -> Optional[datetime]:
        """Parse RSS pubDate to datetime"""
        if not pub_date_str:
            return None
        
        # Common RSS date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 with timezone
            "%a, %d %b %Y %H:%M:%S GMT",  # GMT format
            "%a, %d %b %Y %H:%M:%S",     # Without timezone
            "%Y-%m-%dT%H:%M:%S%z",       # ISO format
        ]
        
        # Clean up the date string - handle +1200 format
        cleaned_date = pub_date_str.strip()
        
        for fmt in formats:
            try:
                # Try parsing with timezone first
                if "%z" in fmt:
                    return datetime.strptime(cleaned_date, fmt)
                else:
                    # Parse without timezone and make it timezone-aware (assume UTC)
                    dt = datetime.strptime(cleaned_date, fmt)
                    from datetime import timezone
                    return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        # If all formats fail, try to extract just the date part
        try:
            import re
            # Extract date components: "Sat, 7 Jun 2025 17:29:03 +1200"
            date_match = re.match(r"(\w+),\s*(\d+)\s+(\w+)\s+(\d+)\s+(\d+):(\d+):(\d+)", cleaned_date)
            if date_match:
                day, month_name, year, hour, minute, second = date_match.groups()[1:7]
                
                # Convert month name to number
                months = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month = months.get(month_name, 1)
                
                from datetime import timezone
                return datetime(
                    int(year), month, int(day), 
                    int(hour), int(minute), int(second),
                    tzinfo=timezone.utc
                )
        except Exception:
            pass
        
        logger.warning(f"Could not parse date format: {pub_date_str}")
        return None
    
    async def close(self):
        """Clean up HTTP session"""
        await self.session.aclose()