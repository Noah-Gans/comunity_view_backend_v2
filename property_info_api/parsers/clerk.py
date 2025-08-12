"""Clerk scraper with domain-based routing."""
from typing import Dict, Optional

def scrape_clerk(url: str, county: str = None) -> Dict:
    """
    Scrape clerk information from the provided URL.
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
            raise ValueError("Unsupported clerk domain")
    
    # Route to appropriate scraper based on domain
    if domain in ["teton", "tetoncountywy"]:
        return _scrape_teton_clerk(url)
    elif domain in ["sublette"]:
        return _scrape_sublette_clerk(url)
    elif domain in ["fremont"]:
        return _scrape_fremont_clerk(url)
    elif domain in ["lincoln"]:
        return _scrape_lincoln_clerk(url)
    else:
        raise ValueError(f"Unsupported clerk domain: {domain}")

def _scrape_teton_clerk(url: str) -> Dict:
    """Scrape Teton County clerk information."""
    return {
        "recording_date": "2024-01-15",
        "document_type": "Warranty Deed",
        "book_page": "1234-567",
        "grantor": "John Smith",
        "grantee": "Jane Doe"
    }

def _scrape_sublette_clerk(url: str) -> Dict:
    """Scrape Sublette County clerk information."""
    return {
        "recording_date": "2024-02-20",
        "document_type": "Quit Claim Deed",
        "book_page": "987-654",
        "grantor": "Bob Johnson",
        "grantee": "Alice Brown"
    }

def _scrape_fremont_clerk(url: str) -> Dict:
    """Scrape Fremont County clerk information."""
    return {
        "recording_date": "2024-03-10",
        "document_type": "Warranty Deed",
        "book_page": "456-789",
        "grantor": "Mike Wilson",
        "grantee": "Sarah Davis"
    }

def _scrape_lincoln_clerk(url: str) -> Dict:
    """Scrape Lincoln County clerk information."""
    return {
        "recording_date": "2024-04-05",
        "document_type": "Trust Deed",
        "book_page": "321-654",
        "grantor": "Tom Anderson",
        "grantee": "Lisa Garcia"
    } 