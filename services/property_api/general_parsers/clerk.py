"""Clerk scraper with domain-based routing and override support."""
from typing import Dict
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

def scrape_clerk(url: str, county: str = None) -> Dict:
    """Route to the correct clerk scraper based on county."""
    logger.info(f"(General Clerk) Starting clerk scrape for county: {county}")
    
    if county == "teton_county_wy":
        try:
            from overrides.clerk.teton_county_wy_wy import scrape_clerk as teton_scrape_clerk
            logger.info(f"(General Clerk) Using Teton County WY clerk scraper")
            result = teton_scrape_clerk(url, county)
            logger.info(f"(General Clerk) Completed Teton County WY clerk scrape")
            return result
        except ImportError as e:
            logger.warning(f"(General Clerk) Failed to import Teton County clerk scraper: {e}")
            result = _scrape_teton_clerk(url, county)
            logger.info(f"(General Clerk) Completed fallback Teton County clerk scrape")
            return result
    elif "tetoncountywy.gov" in url:
        try:
            from overrides.clerk.teton_county_wy_wy import scrape_clerk as teton_scrape_clerk
            logger.info(f"(General Clerk) Using Teton County WY clerk scraper (URL-based)")
            result = teton_scrape_clerk(url, county)
            logger.info(f"(General Clerk) Completed Teton County WY clerk scrape")
            return result
        except ImportError:
            logger.warning(f"(General Clerk) Failed to import Teton County clerk scraper, using fallback")
            result = _scrape_teton_clerk(url, county)
            logger.info(f"(General Clerk) Completed fallback Teton County clerk scrape")
            return result
    
    # For other counties, return placeholder
    logger.info(f"(General Clerk) Clerk scraping not implemented for county: {county}")
    return {"message": "Clerk scraping not implemented", "source": f"clerk_scraper_{county}"}

def _scrape_teton_clerk(url: str, county: str = None) -> Dict:
    """Mock Teton County clerk scraper."""
    logger.debug(f"(General Clerk) Using fallback clerk scraper for county: {county}")
    return {"message": "Clerk scraping not implemented", "source": f"clerk_scraper_{county}"} 