"""Tax scraper with domain-based routing and override support."""
from typing import Dict
from overrides import teton

def scrape_tax(url: str) -> Dict:
    """Route to the correct tax scraper based on domain."""
    if "tetoncountywy.gov" in url:
        if hasattr(teton, "scrape_tax"):
            return teton.scrape_tax(url)
        return _scrape_teton_tax(url)
    raise ValueError("Unsupported tax domain")

def _scrape_teton_tax(url: str) -> Dict:
    """Mock Teton County tax scraper."""
    return {"example": "Teton County tax data", "url": url} 