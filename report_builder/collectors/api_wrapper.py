"""API wrapper to call existing property_info_api scrapers"""

import sys
import os
import asyncio
from typing import Dict, Optional

# Add property_info_api to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'property_info_api'))

from county_config import construct_links
from overrides.tax.tyler_technologies_tax import scrape_tax
from overrides.property_details.greenwood_details_scrape import scrape_property_details
from general_parsers.property_details import GeneralPropertyDetailsScraper, scrape_property_details as general_scrape_property_details
from general_parsers.tax import scrape_tax as general_scrape_tax

class APIWrapper:
    """Wrapper around existing property_info_api scrapers"""
    
    def __init__(self):
        pass
        
    def get_scraping_urls(self, county: str, parcel_data: Dict) -> Dict[str, Optional[str]]:
        """Get URLs for scraping using existing construct_links function"""
        
        # Build fields dict from parcel data
        fields = {}
        
        if parcel_data.get("tax_details_key"):
            fields["tax_field"] = parcel_data["tax_details_key"]
            
        if parcel_data.get("property_details_key"):
            fields["property_details_field"] = parcel_data["property_details_key"]
            
        if parcel_data.get("clerk_records_key"):
            fields["clerk_field"] = parcel_data["clerk_records_key"]
            
        # Use existing construct_links function
        try:
            links = construct_links(county, fields)
            return links
        except Exception as e:
            print(f"Error constructing links for {county}: {e}")
            return {}
    
    async def scrape_tax_data(self, county: str, url: str) -> Optional[Dict]:
        """Scrape tax data using existing scrapers"""
        if not url:
            return None
            
        try:
            # Use existing scraper based on county type
            if county in ["lincoln_county_wy", "fremont_county_wy", "sublette_county_wy"]:
                # Tyler Technologies counties
                result = scrape_tax(url, county=county)
            else:
                # Other counties - use general tax scraper function
                result = general_scrape_tax(url, county=county)
                
            return result
            
        except Exception as e:
            print(f"Error scraping tax data for {county} at {url}: {e}")
            return {"error": str(e), "source": f"tax_scraper_{county}"}
    
    async def scrape_property_data(self, county: str, url: str) -> Optional[Dict]:
        """Scrape property details using existing scrapers"""
        if not url:
            return None
            
        try:
            # Use existing scraper - the general function handles routing
            result = general_scrape_property_details(url, config={"county": county})
                
            return result
            
        except Exception as e:
            print(f"Error scraping property data for {county} at {url}: {e}")
            return {"error": str(e), "source": f"property_scraper_{county}"}
    
    async def scrape_clerk_data(self, county: str, url: str) -> Optional[Dict]:
        """Scrape clerk data - placeholder for future implementation"""
        if not url:
            return None
            
        # Clerk scraping not implemented yet
        return {"message": "Clerk scraping not implemented", "source": f"clerk_scraper_{county}"}
    
    async def collect_parcel_data(self, county: str, parcel_data: Dict) -> Dict:
        """Collect all data types for a single parcel"""
        
        # Get scraping URLs
        urls = self.get_scraping_urls(county, parcel_data)
        
        result = {
            "parcel_id": parcel_data.get("county_parcel_id"),
            "property_details_key": parcel_data.get("property_details_key"),
            "tax_details_key": parcel_data.get("tax_details_key"),
            "county": county,
            "owner_name": parcel_data.get("owner_name"),
            "physical_address": parcel_data.get("physical_address"),
            "acres": parcel_data.get("acres"),
            "collection_timestamp": None,  # Will be set by caller
            "scraped_data": {},
            "errors": []
        }
        
        # Scrape tax data
        if urls.get("tax_field"):
            tax_data = await self.scrape_tax_data(county, urls["tax_field"])
            if tax_data:
                result["scraped_data"]["tax_data"] = tax_data
                if tax_data.get("error"):
                    result["errors"].append(f"Tax scraping: {tax_data['error']}")
        else:
            # No tax key available - create placeholder
            result["scraped_data"]["tax_data"] = {
                "status": "no_tax_key",
                "reason": "Parcel has no tax_details_key in GeoJSON",
                "county": county,
                "scraped": False
            }
        
        # Scrape property data
        if urls.get("property_details_field"):
            property_data = await self.scrape_property_data(county, urls["property_details_field"])
            if property_data:
                result["scraped_data"]["property_data"] = property_data
                if property_data.get("error"):
                    result["errors"].append(f"Property scraping: {property_data['error']}")
        else:
            # No property key available - create placeholder
            result["scraped_data"]["property_data"] = {
                "status": "no_property_key", 
                "reason": "Parcel has no property_details_key in GeoJSON",
                "county": county,
                "scraped": False
            }
        
        # Scrape clerk data (placeholder)
        if urls.get("clerk_field"):
            clerk_data = await self.scrape_clerk_data(county, urls["clerk_field"])
            if clerk_data:
                result["scraped_data"]["clerk_data"] = clerk_data
        else:
            # No clerk key available - create placeholder
            result["scraped_data"]["clerk_data"] = {
                "status": "no_clerk_key",
                "reason": "Parcel has no clerk_records_key in GeoJSON", 
                "county": county,
                "scraped": False
            }
        
        return result
