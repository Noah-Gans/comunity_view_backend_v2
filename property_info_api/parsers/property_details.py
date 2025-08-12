"""Property details scraper module."""
from general_parsers.property_details import scrape_property_details as general_scrape_property_details

def scrape_property_details(url: str, config: dict = None) -> dict:
    """
    Scrape property details from the provided URL.
    Uses the general property details scraper with optional county-specific overrides.
    """
    return general_scrape_property_details(url, config) 