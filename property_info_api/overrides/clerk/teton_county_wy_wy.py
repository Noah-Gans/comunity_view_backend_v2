# Save as: property_info_api/overrides/clerk/teton_county_wy_clerk.py

"""Teton County Wyoming clerk records scraper using direct API calls."""
import requests
from typing import Dict
from datetime import datetime

def scrape_clerk(url: str, county: str = None) -> Dict:
    """Scrape clerk records from Teton County Wyoming using direct API calls."""
    try:
        print(f"[TETON_CLERK] Scraping Teton County WY clerk URL: {url}")
        start_time = datetime.now()
        
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
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
        print(f"[TETON_CLERK] Scraping completed in {processing_time:.2f} seconds")
        
        return result
        
    except Exception as e:
        print(f"[TETON_CLERK] Error: {e}")
        return {"error": str(e), "source": "teton_county_wy_clerk"}

def print_clerk_summary(clerk_data: Dict) -> None:
    """Print a summary of the clerk data."""
    print("\n" + "="*80)
    print("️ TETON COUNTY WYOMING CLERK RECORDS SUMMARY")
    print("="*80)
    
    records_count = clerk_data.get('records_count', 0)
    print(f"📄 Total Records Found: {records_count}")
    
    if records_count > 0:
        api_response = clerk_data.get('api_response', {})
        features = api_response.get('features', [])
        
        # Show first few record types
        record_types = {}
        for feature in features[:10]:  # Check first 10 records
            attrs = feature.get('attributes', {})
            record_type = attrs.get('description', 'UNKNOWN')
            record_types[record_type] = record_types.get(record_type, 0) + 1
        
        print(f"\n📋 Record Types Found:")
        for record_type, count in record_types.items():
            print(f"   • {record_type}: {count}")
        
        if records_count > 10:
            print(f"   ... and {records_count - 10} more records")
    
    print("="*80)
