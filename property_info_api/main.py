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
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'property_info_api'))
from storage.db import init_db, get_latest_raw, save_raw
from fastapi.responses import StreamingResponse
import asyncio
import logging

# Setup logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

class ScrapeRequest(BaseModel):
    county: str  # County name (e.g., "teton_county_wy", "sublette_county_wy")
    county_parcel_id: Optional[str] = None  # New: explicit DB lookup key
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
    logger.debug(f"Raw data saved to {filename}")
    return filename

def flatten_raw_data(raw_data):
    """Flatten nested data structure to match DataStandardizer expectations"""
    flattened = {}
    
    # Flatten tax data
    if raw_data and raw_data.get("tax_raw_data"):
        tax_data = raw_data["tax_raw_data"]
        if tax_data and "tax_data" in tax_data:
            tax_info = tax_data["tax_data"]
            flattened["tax_id"] = tax_info.get("tax_id")
            
            # Flatten current_tax fields
            if "current_tax" in tax_info:
                current_tax = tax_info["current_tax"]
                flattened["tax_year"] = current_tax.get("tax_year")
                flattened["owner_name"] = current_tax.get("owner_name")
                flattened["total_tax_levied"] = current_tax.get("total_tax_levied")
                flattened["tax_received"] = current_tax.get("tax_received")
                flattened["amount_due"] = current_tax.get("amount_due")
                flattened["status"] = current_tax.get("status")
                
                # Flatten first_half and second_half
                if "first_half" in current_tax:
                    first_half = current_tax["first_half"]
                    flattened["first_half_levied"] = first_half.get("levied")
                    flattened["first_half_paid"] = first_half.get("paid")
                
                if "second_half" in current_tax:
                    second_half = current_tax["second_half"]
                    flattened["second_half_levied"] = second_half.get("levied")
                    flattened["second_half_paid"] = second_half.get("paid")
            
            # Flatten historical data
            if "historical_taxes" in tax_info:
                flattened["historical_data"] = tax_info["historical_taxes"]
    
    # Flatten property data
    if raw_data and raw_data.get("property_raw_data"):
        property_data = raw_data["property_raw_data"]
        if property_data and "property_data" in property_data:
            prop_info = property_data["property_data"]
            flattened["county_parcel_id"] = prop_info.get("county_parcel_id")
            flattened["tax_id"] = prop_info.get("tax_id")
            flattened["physical_address"] = prop_info.get("physical_address")
            flattened["mailing_address"] = prop_info.get("mailing_address")
            flattened["owner_name"] = prop_info.get("owner_name")
            flattened["total_acres"] = prop_info.get("total_acres")
            
            # Flatten value_summary
            if "value_summary" in prop_info:
                value_summary = prop_info["value_summary"]
                flattened["total_property_value"] = value_summary.get("total_value")
                flattened["land_value"] = value_summary.get("land")
                flattened["developments_value"] = value_summary.get("developments")
            
            # Flatten acreage_breakdown
            if "acreage_breakdown" in prop_info:
                flattened["acreage_breakdown"] = prop_info["acreage_breakdown"]
            
            # Flatten developments
            if "developments" in prop_info:
                flattened["developments"] = prop_info["developments"]
                flattened["num_developments"] = len(prop_info["developments"])
    
    return flattened

@app.post("/scrape")
async def scrape_property_info(request: ScrapeRequest):
    """
    Scrape property information by checking database first, then scraping if needed.
    """
    try:
        logger.info(f"Received request for county: {request.county}")
        logger.info(f"County parcel id: {request.county_parcel_id}")
        logger.debug(f"Fields: {json.dumps(request.fields, indent=2, ensure_ascii=False)}")
        
        # Try DB first: (county, county_parcel_id)
        if request.county_parcel_id:
            logger.info(f"DB lookup by county_parcel_id: {request.county_parcel_id}")
            raw_data = get_latest_raw(request.county, request.county_parcel_id)
            logger.debug(f"Raw data: {json.dumps(raw_data, indent=2, ensure_ascii=False)}")
            
            if raw_data:
                logger.info(f"DB HIT via county_parcel_id={request.county_parcel_id}")
                
                # Extract the inner data structures that DataStandardizer expects
                tax_data = None
                if raw_data.get("tax_raw_data"):
                    tax_data = raw_data["tax_raw_data"].get("tax_data")
                
                property_data = None
                if raw_data.get("property_raw_data"):
                    property_data = raw_data["property_raw_data"].get("property_data")
                
                clerk_data = None
                if raw_data.get("clerk_raw_data"):
                    clerk_data = raw_data["clerk_raw_data"].get("clerk_data")
                
                standardized_response = DataStandardizer.standardize_api_response(
                    tax_data,
                    property_data,
                    clerk_data,
                    request.county,
                    county_links=raw_data.get("county_links")
                )
                logger.debug(f"Final standardized response: {json.dumps(standardized_response, indent=2, ensure_ascii=False)}")
                return standardized_response
            else:
                logger.info(f"DB MISS via county_parcel_id={request.county_parcel_id}")
        else:
            logger.info("No county_parcel_id provided. Falling back to live scraping")
        
        # If not in database, fall back to existing scraping logic
        logger.info("No DB match found. Falling back to live scraping")
        
        # Initialize raw data variables
        raw_tax_data = None
        raw_property_data = None
        raw_clerk_data = None
        
        # Special handling for Teton Idaho (database-based)
        if request.county == "teton_county_id":
            if request.fields.get("property_details_field"):
                try:
                    parcel_id = request.fields["property_details_field"]
                    logger.info(f"Calling Teton Idaho scraper with parcel ID: {parcel_id}")
                    raw_property_data = property_details_parser.scrape_property_details(
                        parcel_id, 
                        config={"county": request.county}
                    )
                except Exception as e:
                    logger.error(f"Teton Idaho scraper error: {e}")
                    raw_property_data = {"error": str(e), "source": f"property_scraper_{request.county}"}
        else:
            # Normal flow for other counties
            links = construct_links(request.county, request.fields)
            logger.debug(f"Constructed links: {json.dumps(links, indent=2, ensure_ascii=False)}")
            
            # Process each constructed link
            if "tax_field" in links:
                try:
                    logger.info(f"Calling tax scraper with URL: {links['tax_field']}")
                    raw_tax_data = tax_parser.scrape_tax(links["tax_field"], county=request.county)
                except Exception as e:
                    logger.error(f"Tax scraper error: {e}")
                    raw_tax_data = {"error": str(e), "source": f"tax_scraper_{request.county}"}
            
            if "clerk_field" in links:
                try:
                    logger.info(f"Calling clerk scraper with URL: {links['clerk_field']}")
                    raw_clerk_data = clerk_parser.scrape_clerk(links["clerk_field"], county=request.county)
                except Exception as e:
                    logger.error(f"Clerk scraper error: {e}")
                    raw_clerk_data = {"error": str(e), "source": f"clerk_scraper_{request.county}"}
            
            if "property_details_field" in links:
                try:
                    logger.info(f"Calling property details scraper with URL: {links['property_details_field']}")
                    raw_property_data = property_details_parser.scrape_property_details(
                        links["property_details_field"], 
                        config={"county": request.county}
                    )
                except Exception as e:
                    logger.error(f"Property details scraper error: {e}")
                    raw_property_data = {"error": str(e), "source": f"property_scraper_{request.county}"}
        
        # Standardize all data into consistent format
        standardized_response = DataStandardizer.standardize_api_response(
            raw_tax_data, raw_property_data, raw_clerk_data, request.county, county_links=links if 'links' in locals() else None
        )
        
        logger.debug(f"Final standardized response: {json.dumps(standardized_response, indent=2, ensure_ascii=False)}")
        
        # Capture raw data for config creation
        config_file = capture_raw_data_for_config(raw_tax_data, raw_property_data, raw_clerk_data, request.county)
        
        return standardized_response
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")

@app.post("/scrape-stream")
async def scrape_property_stream(request: ScrapeRequest):
    """
    Stream property information: send cached data first, then fresh scraped data.
    Returns Server-Sent Events (SSE) for real-time updates.
    """
    # Add timing
    import time
    start_time = time.time()
    logger.info(f"⏰ STREAM START: {start_time}")
    
    async def event_generator():
        try:
            # Step 2 & 3: Query DB and send cached data immediately
            if request.county_parcel_id:
                # LOG: Check what's in database BEFORE querying
                logger.info(f"🔍 BEFORE DB QUERY - Checking database for {request.county} / {request.county_parcel_id}")
                
                # Query the database
                raw_data = get_latest_raw(request.county, request.county_parcel_id)
                
                if raw_data:
                    logger.info(f"✅ DB HIT - Found cached data for {request.county} / {request.county_parcel_id}")
                    
                    # LOG: Show what we found in the database
                    logger.info(f"📊 DATABASE CONTENTS:")
                    logger.info(f"   - Tax data exists: {bool(raw_data.get('tax_raw_data'))}")
                    logger.info(f"   - Property data exists: {bool(raw_data.get('property_raw_data'))}")
                    logger.info(f"   - Clerk data exists: {bool(raw_data.get('clerk_raw_data'))}")
                    logger.info(f"   - Source: {raw_data.get('source', 'unknown')}")
                    logger.info(f"   - Collected at: {raw_data.get('collected_at', 'unknown')}")
                    
                    # Add this right after we get raw_data from the database:
                    logger.info(f"🔍 RAW_DATA STRUCTURE FROM DATABASE:")
                    logger.info(f"   - raw_data type: {type(raw_data)}")
                    logger.info(f"   - raw_data keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Not a dict'}")
                    logger.info(f"   - tax_raw_data exists: {'tax_raw_data' in raw_data}")
                    logger.info(f"   - property_raw_data exists: {'property_raw_data' in raw_data}")
                    logger.info(f"   - clerk_raw_data exists: {'clerk_raw_data' in raw_data}")
                    if 'tax_raw_data' in raw_data:
                        logger.info(f"   - tax_raw_data type: {type(raw_data['tax_raw_data'])}")
                    if 'property_raw_data' in raw_data:
                        logger.info(f"   - property_raw_data type: {type(raw_data['property_raw_data'])}")
                    if 'clerk_raw_data' in raw_data:
                        logger.info(f"   - clerk_raw_data type: {type(raw_data['clerk_raw_data'])}")
                    
                    # Null-safe extraction for possibly-missing sections
                    tax_section = raw_data.get("tax_raw_data") or {}
                    prop_section = raw_data.get("property_raw_data") or {}
                    clerk_section = raw_data.get("clerk_raw_data") or {}

                    if isinstance(tax_section, dict):
                        # Handle both formats: nested "tax_data" or direct format
                        if "tax_data" in tax_section:
                            tax_data = tax_section["tax_data"]  # Old format
                        else:
                            tax_data = tax_section  # New format (direct)
                    else:
                        tax_data = None

                    if isinstance(prop_section, dict):
                        if "property_data" in prop_section:
                            property_data = prop_section["property_data"]  # Old format
                        else:
                            property_data = prop_section  # New format (direct)
                    else:
                        property_data = None

                    if isinstance(clerk_section, dict):
                        if "clerk_data" in clerk_section:
                            clerk_data = clerk_section["clerk_data"]  # Old format
                        else:
                            clerk_data = clerk_section  # New format (direct)
                    else:
                        clerk_data = None

                    logger.info(f"(API) Tax data being passed to DataStandardizer: {tax_data}")
                    logger.info(f"(API) Property data being passed to DataStandardizer: {property_data}")
                    logger.info(f"(API) Clerk data being passed to DataStandardizer: {clerk_data}")

                    logger.info(f"🔍 DATA BEING PASSED TO STANDARDIZER (cached):")
                    logger.info(f"   - tax_data type: {type(tax_data)}")
                    logger.info(f"   - tax_data keys: {list(tax_data.keys()) if isinstance(tax_data, dict) else 'Not a dict'}")
                    logger.info(f"   - property_data type: {type(property_data)}")
                    logger.info(f"   - property_data keys: {list(property_data.keys()) if isinstance(property_data, dict) else 'Not a dict'}")
                    logger.info(f"   - clerk_data type: {type(clerk_data)}")
                    logger.info(f"   - clerk_data keys: {list(clerk_data.keys()) if isinstance(clerk_data, dict) else 'Not a dict'}")

                    cached_response = DataStandardizer.standardize_api_response(
                        tax_data, property_data, clerk_data,
                        request.county,
                        county_links=raw_data.get("county_links") or {}
                    )

                    logger.info(f"📤 STANDARDIZER RESPONSE (cached):")
                    logger.info(f"   - Response type: {type(cached_response)}")
                    logger.info(f"   - Has 'data' key: {'data' in cached_response if isinstance(cached_response, dict) else False}")
                    if isinstance(cached_response, dict) and 'data' in cached_response:
                        logger.info(f"   - Data keys: {list(cached_response['data'].keys())}")

                    # Add timing before first yield
                    cached_time = time.time()
                    elapsed = cached_time - start_time
                    logger.info(f"⏰ FIRST YIELD (cached): {cached_time} - Elapsed: {elapsed:.3f}s")
                    
                    # Send only the inner 'data' part (remove outer wrapper)
                    yield f"data: {json.dumps({'status': 'cached', 'data': cached_response['data']})}\n\n"
                else:
                    logger.info(f"❌ DB MISS - No cached data found for {request.county} / {request.county_parcel_id}")
            
            # Step 4: Scrape fresh data
            logger.info("(API) Onto Scraping fresh data")
            if request.county == "teton_county_id" and request.county_parcel_id:
                logger.info("(API) Teton County Idaho - skipping fresh scrape (all data in database)")
                # Skip to completion without updating database
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                return
            links = construct_links(request.county, request.fields)
            
            # Scrape all sources
            raw_tax_data = None
            raw_property_data = None
            raw_clerk_data = None
            
            if "tax_field" in links:
                logger.info(f"(API) Calling tax scraper")
                raw_tax_data = await asyncio.to_thread(
                    tax_parser.scrape_tax, links["tax_field"], county=request.county
                )
                logger.debug(f"(API) Raw tax data: {json.dumps(raw_tax_data, indent=2, ensure_ascii=False)}")
            
            if "property_details_field" in links:
                logger.info(f"(API) Calling property details scraper")
                raw_property_data = await asyncio.to_thread(
                    property_details_parser.scrape_property_details,
                    links["property_details_field"], 
                    config={"county": request.county}
                )
                logger.debug(f"(API) Raw property data: {json.dumps(raw_property_data, indent=2, ensure_ascii=False)}")
            if "clerk_field" in links:
                logger.info(f"(API) Calling clerk scraper")
                raw_clerk_data = await asyncio.to_thread(
                    clerk_parser.scrape_clerk, links["clerk_field"], county=request.county
                )
            
            # LOG: Show what we scraped
            logger.info(f"🔄 FRESH SCRAPED DATA:")
            logger.info(f"   - Tax data scraped: {bool(raw_tax_data)}")
            logger.info(f"   - Property data scraped: {bool(raw_property_data)}")
            logger.info(f"   - Clerk data scraped: {bool(raw_clerk_data)}")
            
            # After scraping fresh data, add this detailed logging:
            if raw_tax_data:
                logger.info(f"💰 FRESH TAX DATA TO SAVE:")
                logger.info(f"   - Type: {type(raw_tax_data)}")
                logger.info(f"   - Keys: {list(raw_tax_data.keys()) if isinstance(raw_tax_data, dict) else 'Not a dict'}")
                if isinstance(raw_tax_data, dict) and 'tax_data' in raw_tax_data:
                    tax_inner = raw_tax_data['tax_data']
                    logger.info(f"   - Tax ID: {tax_inner.get('tax_id', 'N/A')}")
                    logger.info(f"   - Owner: {tax_inner.get('current_tax', {}).get('owner_name', 'N/A')}")
                logger.info(f"   - Full tax data: {json.dumps(raw_tax_data, indent=2)[:500]}...")

            if raw_property_data:
                logger.info(f"🏠 FRESH PROPERTY DATA TO SAVE:")
                logger.info(f"   - Type: {type(raw_property_data)}")
                logger.info(f"   - Keys: {list(raw_property_data.keys()) if isinstance(raw_property_data, dict) else 'Not a dict'}")
                if isinstance(raw_property_data, dict) and 'property_data' in raw_property_data:
                    prop_inner = raw_property_data['property_data']
                    logger.info(f"   - Parcel ID: {prop_inner.get('county_parcel_id', 'N/A')}")
                    logger.info(f"   - Owner: {prop_inner.get('owner_name', 'N/A')}")
                logger.info(f"   - Full property data: {json.dumps(raw_property_data, indent=2)[:500]}...")

            if raw_clerk_data:
                logger.info(f"📋 FRESH CLERK DATA TO SAVE:")
                logger.info(f"   - Type: {type(raw_clerk_data)}")
                logger.info(f"   - Keys: {list(raw_clerk_data.keys()) if isinstance(raw_clerk_data, dict) else 'Not a dict'}")
                if isinstance(raw_clerk_data, dict) and 'clerk_data' in raw_clerk_data:
                    clerk_inner = raw_clerk_data['clerk_data']
                    logger.info(f"   - Records count: {clerk_inner.get('records_count', 0)}")

            # Step 6: Update database with fresh data
            if request.county_parcel_id:
                logger.info(f"💾 BEFORE DB UPDATE - About to save fresh data for {request.county} / {request.county_parcel_id}")
                
                # Before saving to database, log what we're about to save:
                save_bundle = {
                    "tax_raw_data": raw_tax_data,
                    "property_raw_data": raw_property_data,
                    "clerk_raw_data": raw_clerk_data,
                    "county_links": links,
                    "source": "api_scrape_refresh"
                }

                logger.info(f"💾 BUNDLE TO SAVE TO DATABASE:")
                logger.info(f"   - Tax data in bundle: {bool(save_bundle['tax_raw_data'])}")
                logger.info(f"   - Property data in bundle: {bool(save_bundle['property_raw_data'])}")
                logger.info(f"   - Clerk data in bundle: {bool(save_bundle['clerk_raw_data'])}")
                logger.info(f"   - Bundle keys: {list(save_bundle.keys())}")

                await asyncio.to_thread(
                    save_raw, request.county, request.county_parcel_id, save_bundle
                )
                
                logger.info(f"✅ AFTER DB UPDATE - Fresh data saved for {request.county} / {request.county_parcel_id}")
                
                # After saving, add verification with detailed content:
                verify_data = get_latest_raw(request.county, request.county_parcel_id)
                if verify_data:
                    logger.info(f"🔍 VERIFICATION - RETRIEVED DATA FROM DATABASE:")
                    logger.info(f"   - Tax data retrieved: {bool(verify_data.get('tax_raw_data'))}")
                    logger.info(f"   - Property data retrieved: {bool(verify_data.get('property_raw_data'))}")
                    logger.info(f"   - Clerk data retrieved: {bool(verify_data.get('clerk_raw_data'))}")
                    
                    # Check the actual content of retrieved data
                    if verify_data.get('tax_raw_data'):
                        retrieved_tax = verify_data['tax_raw_data']
                        logger.info(f"   - Retrieved tax type: {type(retrieved_tax)}")
                        if isinstance(retrieved_tax, dict):
                            logger.info(f"   - Retrieved tax keys: {list(retrieved_tax.keys())}")
                            if 'tax_data' in retrieved_tax:
                                tax_inner = retrieved_tax['tax_data']
                                logger.info(f"   - Retrieved tax ID: {tax_inner.get('tax_id', 'N/A')}")
                    
                    if verify_data.get('property_raw_data'):
                        retrieved_prop = verify_data['property_raw_data']
                        logger.info(f"   - Retrieved property type: {type(retrieved_prop)}")
                        if isinstance(retrieved_prop, dict):
                            logger.info(f"   - Retrieved property keys: {list(retrieved_prop.keys())}")
                            if 'property_data' in retrieved_prop:
                                prop_inner = retrieved_prop['property_data']
                                logger.info(f"   - Retrieved parcel ID: {prop_inner.get('county_parcel_id', 'N/A')}")
                else:
                    logger.error(f"❌ VERIFICATION FAILED - No data found after save!")
                
                logger.info("(API) Updated database with fresh data")
            
            # Step 5: Send fresh data to client
            fresh_response = DataStandardizer.standardize_api_response(
                raw_tax_data, raw_property_data, raw_clerk_data,
                request.county,
                county_links=links
            )
            
            # Add timing before second yield
            fresh_time = time.time()
            elapsed = fresh_time - start_time
            logger.info(f"⏰ SECOND YIELD (fresh): {fresh_time} - Elapsed: {elapsed:.3f}s")
            
            # Send only the inner 'data' part (remove outer wrapper)
            yield f"data: {json.dumps({'status': 'fresh', 'data': fresh_response['data']})}\n\n"
            
            # Signal completion
            complete_time = time.time()
            elapsed = complete_time - start_time
            logger.info(f"⏰ THIRD YIELD (complete): {complete_time} - Elapsed: {elapsed:.3f}s")
            logger.info("(API) Stream completed successfully")
            yield f"data: {json.dumps({'status': 'complete'})}\n\n"
            
        except Exception as e:
            error_time = time.time()
            elapsed = error_time - start_time
            logger.error(f"⏰ ERROR at {error_time} - Elapsed: {elapsed:.3f}s")
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 