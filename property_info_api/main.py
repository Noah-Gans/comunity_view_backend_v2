from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, Any
import general_parsers.tax as tax_parser
import general_parsers.clerk as clerk_parser
import general_parsers.property_details as property_details_parser
from county_config import construct_links
from data_standardizer import DataStandardizer
import json
from datetime import datetime

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    county: str  # County name (e.g., "teton_county_wy", "sublette_county_wy")
    fields: Dict[str, Optional[str]]  # {"tax_field": "12345", "property_details_field": "67890", "clerk_field": ""}

def capture_raw_data_for_config(tax_data, property_data, clerk_data, county):
    """Capture raw data for config creation."""
    raw_data = {
        "timestamp": datetime.now().isoformat(),
        "county": county,
        "tax_data": tax_data,
        "property_data": property_data,
        "clerk_data": clerk_data
    }
    
    filename = f"{county}_raw_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(raw_data, f, indent=2)
    print(f"[CONFIG] Raw data saved to {filename}")
    return filename

@app.post("/scrape")
async def scrape_property_info(request: ScrapeRequest):
    """
    Scrape property information by constructing URLs from field values and county config.
    """
    try:
        print(f"[API] Received request for county: {request.county}")
        print(f"[API] Fields:")
        print(json.dumps(request.fields, indent=2, ensure_ascii=False))
        
        # Initialize raw data variables
        raw_tax_data = None
        raw_property_data = None
        raw_clerk_data = None
        
        # Special handling for Teton Idaho (database-based)
        if request.county == "teton_county_id":
            if request.fields.get("property_details_field"):
                try:
                    parcel_id = request.fields["property_details_field"]
                    print(f"[API] Calling Teton Idaho scraper directly with parcel ID: {parcel_id}")
                    # Pass the parcel ID directly as the "URL"
                    raw_property_data = property_details_parser.scrape_property_details(
                        parcel_id, 
                        config={"county": request.county}
                    )
                except Exception as e:
                    print(f"Teton Idaho scraper error: {e}")
                    raw_property_data = {"error": str(e), "source": f"property_scraper_{request.county}"}
        else:
            # Normal flow for other counties
            links = construct_links(request.county, request.fields)
            print(f"[API] Constructed links:")
            print(json.dumps(links, indent=2, ensure_ascii=False))
            
            # Process each constructed link
            if "tax_field" in links:
                try:
                    print(f"[API] Calling tax scraper with URL: {links['tax_field']}")
                    raw_tax_data = tax_parser.scrape_tax(links["tax_field"], county=request.county)
                except Exception as e:
                    print(f"Tax scraper error: {e}")
                    raw_tax_data = {"error": str(e), "source": f"tax_scraper_{request.county}"}
            
            if "clerk_field" in links:
                try:
                    print(f"[API] Calling clerk scraper with URL: {links['clerk_field']}")
                    raw_clerk_data = clerk_parser.scrape_clerk(links["clerk_field"], county=request.county)
                except Exception as e:
                    print(f"Clerk scraper error: {e}")
                    raw_clerk_data = {"error": str(e), "source": f"clerk_scraper_{request.county}"}
            
            if "property_details_field" in links:
                try:
                    print(f"[API] Calling property details scraper with URL: {links['property_details_field']}")
                    raw_property_data = property_details_parser.scrape_property_details(
                        links["property_details_field"], 
                        config={"county": request.county}
                    )
                except Exception as e:
                    print(f"Property details scraper error: {e}")
                    raw_property_data = {"error": str(e), "source": f"property_scraper_{request.county}"}
        
        # Debug prints for raw data (excluding historical data)
        print(f"[API] Raw tax data before standardization:")
        if raw_tax_data:
            tax_data_for_print = raw_tax_data.copy()
            if "historical_taxes" in tax_data_for_print:
                tax_data_for_print["historical_taxes"] = f"[{len(tax_data_for_print['historical_taxes'])} historical records]"
            if "historical_data" in tax_data_for_print:
                tax_data_for_print["historical_data"] = f"[{len(tax_data_for_print['historical_data'])} historical records]"
            print(json.dumps(tax_data_for_print, indent=2, ensure_ascii=False))
        else:
            print("None")
        
        print(f"[API] Raw property data before standardization:")
        print(json.dumps(raw_property_data, indent=2, ensure_ascii=False))
        
        print(f"[API] Raw clerk data before standardization:")
        print(json.dumps(raw_clerk_data, indent=2, ensure_ascii=False))
        
        # Standardize all data into consistent format
        standardized_response = DataStandardizer.standardize_api_response(
            raw_tax_data, raw_property_data, raw_clerk_data, request.county, county_links=links
        )
        
        print(f"[API] Final standardized response:")
        print(json.dumps(standardized_response, indent=2, ensure_ascii=False))
        
        # Capture raw data for config creation
        config_file = capture_raw_data_for_config(raw_tax_data, raw_property_data, raw_clerk_data, request.county)
        
        return standardized_response
        
    except Exception as e:
        print(f"[API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 