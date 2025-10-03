"""Tax scraper with domain-based routing and override support."""
from typing import Dict, Optional
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

def scrape_tax(url: str, county: str = None) -> Dict:
    """Route to the correct tax scraper based on domain."""
    logger.info(f"(General Tax) Starting tax scraping for: {county}")
    
    if "tetoncountywy.gov" in url:
        try:
            from overrides.tax.teton_county_wy_tax import scrape_tax as teton_scrape_tax
            logger.info("(General Tax) Using Teton County WY tax scraper")
            result = teton_scrape_tax(url)
            logger.info("(General Tax) Completed Teton County WY tax scrape")
            return result
        except ImportError as e:
            logger.warning(f"(General Tax) Teton import error: {e}")
            result = _scrape_teton_tax(url)
            logger.info("(General Tax) Completed fallback Teton County tax scrape")
            return result
    elif "tylertech.com" in url or county in ["fremont_county_wy", "lincoln_county_wy"]:
        try:
            from overrides.tax.tyler_technologies_tax import scrape_tax as tyler_scrape_tax
            logger.info("(General Tax) Using Tyler Technologies tax scraper")
            result = tyler_scrape_tax(url, county)
            logger.info("(General Tax) Completed Tyler Technologies tax scrape")
            return result
        except ImportError as e:
            logger.warning(f"(General Tax) Tyler Technologies import error: {e}")
            result = _scrape_tyler_tax(url, county)
            logger.info("(General Tax) Completed fallback Tyler Technologies tax scrape")
            return result
    elif "terragis.net" in url or county == "sublette_county_wy":
        try:
            from overrides.tax.sublette_county_wy_tax import scrape_tax as sublette_scrape_tax
            logger.info("(General Tax) Using Sublette County WY tax scraper")
            result = sublette_scrape_tax(url, county)
            logger.info("(General Tax) Completed Sublette County WY tax scrape")
            return result   
        except ImportError as e:
            logger.warning(f"(General Tax) Sublette County import error: {e}")
            result = _scrape_sublette_tax(url, county)
            logger.info("(General Tax) Completed fallback Sublette County tax scrape")
            return result
    else:
        logger.warning(f"(General Tax) No specific scraper found for URL: {url}")
        result = {"error": "No scraper available for this URL", "source": "tax_router"}
        logger.info("(General Tax) Completed tax scrape (no scraper available)")
        return result

def _scrape_teton_tax(url: str) -> Dict:
    """Fallback Teton County scraper."""
    logger.warning("(General Tax) Teton County scraper not available")
    return {"error": "Teton County scraper not available", "source": "fallback_teton"}

def _scrape_tyler_tax(url: str, county: str) -> Dict:
    """Fallback Tyler Technologies scraper."""
    logger.warning("(General Tax) Tyler Technologies scraper not available")
    return {"error": "Tyler Technologies scraper not available", "source": "fallback_tyler"}

def _scrape_sublette_tax(url: str, county: str) -> Dict:
    """Fallback Sublette County scraper."""
    logger.warning("(General Tax) Sublette County scraper not available")
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