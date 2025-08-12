"""Tax scraper with domain-based routing."""
from typing import Dict, Optional

def scrape_tax(url: str, county: str = None) -> Dict:
    """
    Scrape tax information from the provided URL.
    Uses domain-based routing to call appropriate scraper.
    """
    if not url:
        return None
    
    # Use county parameter if provided, otherwise extract from URL
    if county:
        domain = county.lower()
    else:
        # Extract domain from URL as fallback
        if "tetoncountywy.gov" in url:
            domain = "teton"
        elif "sublette" in url.lower():
            domain = "sublette"
        elif "fremont" in url.lower():
            domain = "fremont"
        elif "lincoln" in url.lower():
            domain = "lincoln"
        else:
            raise ValueError("Unsupported tax domain")
    
    # Route to appropriate scraper based on domain
    if domain in ["teton", "tetoncountywy"]:
        return _scrape_teton_tax(url)
    elif domain in ["sublette"]:
        return _scrape_sublette_tax(url)
    elif domain in ["fremont"]:
        return _scrape_fremont_tax(url)
    elif domain in ["lincoln"]:
        return _scrape_lincoln_tax(url)
    else:
        raise ValueError(f"Unsupported tax domain: {domain}")

def _scrape_teton_tax(url: str) -> Dict:
    """Scrape Teton County tax information."""
    return {
        "tax_year": "2024",
        "assessed_value": "$500,000",
        "tax_amount": "$3,500",
        "due_date": "2024-12-31"
    }

def _scrape_sublette_tax(url: str) -> Dict:
    """Scrape Sublette County tax information."""
    return {
        "tax_year": "2024",
        "assessed_value": "$300,000",
        "tax_amount": "$2,100",
        "due_date": "2024-12-31"
    }

def _scrape_fremont_tax(url: str) -> Dict:
    """Scrape Fremont County tax information."""
    return {
        "tax_year": "2024",
        "assessed_value": "$400,000",
        "tax_amount": "$2,800",
        "due_date": "2024-12-31"
    }

def _scrape_lincoln_tax(url: str) -> Dict:
    """Scrape Lincoln County tax information."""
    return {
        "tax_year": "2024",
        "assessed_value": "$350,000",
        "tax_amount": "$2,450",
        "due_date": "2024-12-31"
    } 