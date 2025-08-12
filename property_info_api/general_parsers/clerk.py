"""Clerk scraper with domain-based routing and override support."""
from typing import Dict
from overrides import teton

def scrape_clerk(url: str) -> Dict:
    """Route to the correct clerk scraper based on domain."""
    if "tetoncountywy.gov" in url:
        if hasattr(teton, "scrape_clerk"):
            return teton.scrape_clerk(url)
        return _scrape_teton_clerk(url)
    raise ValueError("Unsupported clerk domain")

def _scrape_teton_clerk(url: str) -> Dict:
    """Mock Teton County clerk scraper."""
    return {"example": "Teton County clerk data", "url": url} 