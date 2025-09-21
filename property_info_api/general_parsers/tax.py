"""Tax scraper with domain-based routing and override support."""
from typing import Dict, Optional

def scrape_tax(url: str, county: str = None) -> Dict:
    """Route to the correct tax scraper based on domain."""
    if "tetoncountywy.gov" in url:
        try:
            from overrides.tax.teton_county_wy_tax import scrape_tax as teton_scrape_tax
            return teton_scrape_tax(url)
        except ImportError as e:
            print(f"[TAX] Teton import error: {e}")
            return _scrape_teton_tax(url)
    elif "tylertech.com" in url or county in ["fremont_county_wy", "lincoln_county_wy"]:
        try:
            from overrides.tax.tyler_technologies_tax import scrape_tax as tyler_scrape_tax
            print(f"[TAX] Successfully imported Tyler Technologies scraper")
            return tyler_scrape_tax(url, county)
        except ImportError as e:
            print(f"[TAX] Tyler Technologies import error: {e}")
            return _scrape_tyler_tax(url, county)
    elif "terragis.net" in url or county == "sublette_county_wy":
        try:
            from overrides.tax.sublette_county_wy_tax import scrape_tax as sublette_scrape_tax
            print(f"[TAX] Successfully imported Sublette County scraper")
            return sublette_scrape_tax(url, county)
        except ImportError as e:
            print(f"[TAX] Sublette County import error: {e}")
            return _scrape_sublette_tax(url, county)
    else:
        print(f"[TAX] No specific scraper found for URL: {url}")
        return {"error": "No scraper available for this URL", "source": "tax_router"}

def _scrape_teton_tax(url: str) -> Dict:
    """Fallback Teton County scraper."""
    return {"error": "Teton County scraper not available", "source": "fallback_teton"}

def _scrape_tyler_tax(url: str, county: str) -> Dict:
    """Fallback Tyler Technologies scraper."""
    return {"error": "Tyler Technologies scraper not available", "source": "fallback_tyler"}

def _scrape_sublette_tax(url: str, county: str) -> Dict:
    """Fallback Sublette County scraper."""
    return {"error": "Sublette County scraper not available", "source": "fallback_sublette"}

def clean_amount(amount_str: str) -> Optional[float]:
    """Clean and convert amount string to float."""
    if not amount_str or amount_str.strip() == "" or amount_str.strip() == "&nbsp;":
        return None
    
    # Remove $ and commas
    cleaned = amount_str.replace("$", "").replace(",", "").strip()
    
    # Handle negative amounts
    if cleaned.startswith("-"):
        try:
            return -float(cleaned[1:])
        except ValueError:
            return None
    
    try:
        return float(cleaned)
    except ValueError:
        return None 