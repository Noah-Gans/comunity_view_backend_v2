# Save as: property_info_api/overrides/clerk/teton_county_wy_clerk.py

"""Teton County Wyoming clerk records scraper using direct API calls."""
import requests
from typing import Dict
from datetime import datetime
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

def scrape_clerk(url: str, county: str = None) -> Dict:
    """Scrape clerk records from Teton County Wyoming using direct API calls."""
    try:
        logger.info(f"(Teton County WY Clerk) Starting Teton County WY clerk scrape")
        start_time = datetime.now()
        
        # Extract statepin from the dashboard URL
        if "#statepin=" in url:
            statepin = url.split("#statepin=")[1]
        else:
            # Fallback: try to extract from other URL patterns
            logger.warning(f"(Teton County WY Clerk) Could not extract statepin from URL: {url}")
            return {"error": "Could not extract statepin from URL", "source": "teton_county_wy_clerk"}
        
        # Hardcoded API URL with the extracted statepin
        api_url = f"https://gis.tetoncountywy.gov/server/rest/services/Public_Services/land_records_search/FeatureServer/0/query?f=json&cacheHint=true&resultOffset=0&resultRecordCount=20000&where=statepin%3D%27{statepin}%27&orderByFields=statepin%20ASC%2Cdatetimeoffiling%20DESC&outFields=%2A&resultType=standard&returnGeometry=false&spatialRel=esriSpatialRelIntersects"
        
        logger.debug(f"(Teton County WY Clerk) Using API URL with statepin: {statepin}")
        
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"(Teton County WY Clerk) Retrieved {len(data.get('features', []))} features from API")
        
        # Clean and filter the features
        cleaned_features = []
        for feature in data.get('features', []):
            attrs = feature.get('attributes', {})
            
            # Keep only essential fields
            essential_fields = [
                'entrynumber', 'dateofinstrument', 'datetimeoffiling', 
                'statepin', 'description', 'beginningpage', 'endingpage',
                'record_url', 'book', 'legal', 'grantor', 'grantee',
                'subdivision', 'township', 'range', 'section'
            ]
            
            cleaned_attrs = {k: v for k, v in attrs.items() if k in essential_fields}
            
            # Convert timestamps
            if cleaned_attrs.get('dateofinstrument'):
                cleaned_attrs['dateofinstrument'] = datetime.fromtimestamp(
                    cleaned_attrs['dateofinstrument'] / 1000
                ).strftime('%Y-%m-%d')
            
            if cleaned_attrs.get('datetimeoffiling'):
                cleaned_attrs['datetimeoffiling'] = datetime.fromtimestamp(
                    cleaned_attrs['datetimeoffiling'] / 1000
                ).strftime('%Y-%m-%d')
            
            cleaned_features.append(cleaned_attrs)
        
        result = {
            "records_count": len(cleaned_features),
            "records": cleaned_features,  # Just the cleaned records
            "source": "teton_county_wy_clerk_api",
            "scraped": True,
            "timestamp": datetime.now().isoformat()
        }
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"(Teton County WY Clerk) Scraping completed in {processing_time:.2f} seconds with {len(cleaned_features)} records")
        
        return result
        
    except Exception as e:
        logger.error(f"(Teton County WY Clerk) Error: {e}")
        return {"error": str(e), "source": "teton_county_wy_clerk"}

def print_clerk_summary(clerk_data: Dict) -> None:
    """Print a summary of the clerk data."""
    logger.debug("="*80)
    logger.debug("️ TETON COUNTY WYOMING CLERK RECORDS SUMMARY")
    logger.debug("="*80)
    
    records_count = clerk_data.get('records_count', 0)
    logger.debug(f"📄 Total Records Found: {records_count}")
    
    if records_count > 0:
        api_response = clerk_data.get('api_response', {})
        features = api_response.get('features', [])
        
        # Show first few record types
        record_types = {}
        for feature in features[:10]:  # Check first 10 records
            attrs = feature.get('attributes', {})
            record_type = attrs.get('description', 'UNKNOWN')
            record_types[record_type] = record_types.get(record_type, 0) + 1
        
        logger.debug(f"📋 Record Types Found:")
        for record_type, count in record_types.items():
            logger.debug(f"   • {record_type}: {count}")
        
        if records_count > 10:
            logger.debug(f"   ... and {records_count - 10} more records")
    
    logger.debug("="*80)
