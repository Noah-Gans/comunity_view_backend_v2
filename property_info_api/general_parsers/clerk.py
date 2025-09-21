"""Clerk scraper with domain-based routing and override support."""
from typing import Dict

def scrape_clerk(url: str, county: str = None) -> Dict:
    """Route to the correct clerk scraper based on domain."""
    if "tetoncountywy.gov" in url:
        try:
            from overrides.teton_county_wy_detials import scrape_clerk as teton_scrape_clerk
            return teton_scrape_clerk(url)
        except ImportError:
            return _scrape_teton_clerk(url)
    raise ValueError("Unsupported clerk domain")

def _scrape_teton_clerk(url: str) -> Dict:
    """Mock Teton County clerk scraper."""
    return {"example": "Teton County clerk data", "url": url} 