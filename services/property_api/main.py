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
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from shared.database.storage.db import init_db, get_latest_raw, save_raw
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
    county_parcel_id: Optional[str] = None  # Explicit DB lookup key
    fields: Dict[str, Optional[str]]  # {"tax_field": "12345", "property_details_field": "67890", "clerk_field": ""}

@app.post("/scrape-stream")
async def scrape_property_stream(request: ScrapeRequest):
    """
    Stream property information: send cached data first, then fresh scraped data.
    Returns Server-Sent Events (SSE) for real-time updates.
    """
    async def event_generator():
        try:
            # Query DB and send cached data immediately
            if request.county_parcel_id:
                logger.info(f"🔍 DEBUG: About to query database for {request.county} / {request.county_parcel_id}")
                raw_data = get_latest_raw(request.county, request.county_parcel_id)
                logger.info(f"🔍 DEBUG: Database query result: {type(raw_data)} - {bool(raw_data)}")
                
                if raw_data:
                    logger.info(f"✅ DEBUG: Found cached data, source: {raw_data.get('source')}")
                    
                    # Extract data with robust format handling
                    tax_section = raw_data.get("tax_raw_data") or {}
                    prop_section = raw_data.get("property_raw_data") or {}
                    clerk_section = raw_data.get("clerk_raw_data") or {}

                    # Handle both nested and direct formats
                    if isinstance(tax_section, dict):
                        tax_data = tax_section.get("tax_data", tax_section)
                        logger.info(f"🔍 DEBUG: Tax data extracted - type: {type(tax_data)}, keys: {list(tax_data.keys()) if isinstance(tax_data, dict) else 'None'}")
                    else:
                        tax_data = None
                        logger.info(f"❌ DEBUG: Tax section is not dict: {type(tax_section)}")

                    if isinstance(prop_section, dict):
                        property_data = prop_section.get("property_data", prop_section)
                        logger.info(f"🔍 DEBUG: Property data extracted - type: {type(property_data)}, keys: {list(property_data.keys()) if isinstance(property_data, dict) else 'None'}")
                    else:
                        property_data = None
                        logger.info(f"❌ DEBUG: Property section is not dict: {type(prop_section)}")

                    if isinstance(clerk_section, dict):
                        clerk_data = clerk_section.get("clerk_data", clerk_section)
                        logger.info(f"🔍 DEBUG: Clerk data extracted - type: {type(clerk_data)}, keys: {list(clerk_data.keys()) if isinstance(clerk_data, dict) else 'None'}")
                    else:
                        clerk_data = None
                        logger.info(f"❌ DEBUG: Clerk section is not dict: {type(clerk_section)}")

                    # For cached data:
                    logger.info(f"🔍 DEBUG: DataStandardizer input - CACHED:")
                    if tax_data:
                        logger.info(f"   - tax_data type: {type(tax_data)}")
                        logger.info(f"   - tax_data keys: {list(tax_data.keys())}")
                        if 'current_tax' in tax_data:
                            logger.info(f"   - tax_data.current_tax: {tax_data['current_tax']}")
                        if 'general_info' in tax_data:
                            logger.info(f"   - tax_data.general_info: {tax_data['general_info']}")
                    else:
                        logger.info(f"   - tax_data: None")

                    if property_data:
                        logger.info(f"   - property_data type: {type(property_data)}")
                        logger.info(f"   - property_data keys: {list(property_data.keys())}")
                        if 'owner_name' in property_data:
                            logger.info(f"   - property_data.owner_name: {property_data['owner_name']}")
                        if 'physical_address' in property_data:
                            logger.info(f"   - property_data.physical_address: {property_data['physical_address']}")
                    else:
                        logger.info(f"   - property_data: None")

                    if clerk_data:
                        logger.info(f"   - clerk_data type: {type(clerk_data)}")
                        logger.info(f"   - clerk_data keys: {list(clerk_data.keys())}")
                        if 'records_count' in clerk_data:
                            logger.info(f"   - clerk_data.records_count: {clerk_data['records_count']}")
                    else:
                        logger.info(f"   - clerk_data: None")

                    cached_response = DataStandardizer.standardize_api_response(
                        tax_data, property_data, clerk_data,
                        request.county,
                        county_links=raw_data.get("county_links") or {}
                    )
                    cached_response_data = None
                    if isinstance(cached_response, dict) and 'data' in cached_response:
                        cached_response_data = cached_response['data']
                    
                    logger.info(f"🔍 DEBUG: DataStandardizer cached result:")
                    logger.info(f"   - Response type: {type(cached_response)}")
                    logger.info(f"   - Has 'data' key: {'data' in cached_response if isinstance(cached_response, dict) else False}")
                    if isinstance(cached_response, dict) and 'data' in cached_response:
                        data_sample = str(cached_response['data'])[:200]
                        logger.info(f"   - Data sample: {data_sample}...")
                    logger.info(f"🔍 DEBUG: About to send cached response...")
                    try:
                        response_data = {'status': 'cached', 'data': cached_response['data']}
                        response_json = json.dumps(response_data)
                        logger.info(f"📤 DEBUG: Cached response JSON length: {len(response_json)}")
                        logger.info(f"📤 DEBUG: Cached response sample: {response_json[:200]}...")
                        yield f"data: {response_json}\n\n"
                        logger.info(f"✅ DEBUG: Cached response sent successfully")
                    except Exception as e:
                        logger.error(f"❌ DEBUG: Error sending cached response: {e}")
                else:
                    cached_response_data = None
                    logger.info(f"❌ DEBUG: No cached data found")
            
            # Construct links for fresh scraping
            links = construct_links(request.county, request.fields)
            logger.info(f"🔍 DEBUG: Fresh scraping starting")
            
            if request.county == "teton_county_id" and (not links or all(not v for v in links.values())):
                logger.info("ℹ️  Teton County ID request detected without live links; returning cached data as fresh")
                if cached_response_data:
                    fresh_payload = {'status': 'fresh', 'data': cached_response_data, 'source': 'cache_only'}
                    yield f"data: {json.dumps(fresh_payload)}\n\n"
                else:
                    fallback_payload = {'status': 'fresh', 'data': None, 'message': 'No cached data available'}
                    yield f"data: {json.dumps(fallback_payload)}\n\n"
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                return
            
            # Scrape all sources
            raw_tax_data = None
            raw_property_data = None
            raw_clerk_data = None
            
            if "tax_field" in links:
                raw_tax_data = await asyncio.to_thread(
                    tax_parser.scrape_tax, links["tax_field"], county=request.county
                )
                logger.info(f"💰 DEBUG: Fresh tax data scraped - type: {type(raw_tax_data)}, keys: {list(raw_tax_data.keys()) if isinstance(raw_tax_data, dict) else 'None'}")
            
            if "property_details_field" in links:
                raw_property_data = await asyncio.to_thread(
                    property_details_parser.scrape_property_details,
                    links["property_details_field"], 
                    config={"county": request.county}
                )
                logger.info(f"🏠 DEBUG: Fresh property data scraped - type: {type(raw_property_data)}, keys: {list(raw_property_data.keys()) if isinstance(raw_property_data, dict) else 'None'}")
                
            if "clerk_field" in links:
                raw_clerk_data = await asyncio.to_thread(
                    clerk_parser.scrape_clerk, links["clerk_field"], county=request.county
                )
                logger.info(f"📋 DEBUG: Fresh clerk data scraped - type: {type(raw_clerk_data)}, keys: {list(raw_clerk_data.keys()) if isinstance(raw_clerk_data, dict) else 'None'}")
            
            # Merge additional links from property scraper (for Teton County WY and others)
            final_links = links.copy()
            if raw_property_data and isinstance(raw_property_data, dict):
                additional_links = raw_property_data.get('_additional_links', {})
                if additional_links:
                    final_links.update(additional_links)
                    logger.info(f"🔗 DEBUG: Merged {len(additional_links)} additional links from property scraper")
            
            # Also preserve existing links from previous version (map_no, deed_no, smart_gov, ldr_plan)
            if request.county_parcel_id:
                existing_data = get_latest_raw(request.county, request.county_parcel_id)
                if existing_data and existing_data.get("county_links"):
                    existing_links = existing_data.get("county_links", {})
                    # Preserve map_no, deed_no, smart_gov, ldr_plan if they exist and aren't being updated
                    for key in ['map_no', 'deed_no', 'smart_gov', 'ldr_plan']:
                        if key in existing_links and existing_links[key] and key not in final_links:
                            final_links[key] = existing_links[key]
                            logger.debug(f"🔗 DEBUG: Preserved existing {key} link")
            
            # Update database with fresh data
            if request.county_parcel_id:
                # Clean up _additional_links from property_data before saving (it's just for passing links)
                cleaned_property_data = None
                if raw_property_data and isinstance(raw_property_data, dict):
                    cleaned_property_data = {k: v for k, v in raw_property_data.items() if k != '_additional_links'}
                
                has_new_data = any([raw_tax_data, cleaned_property_data or raw_property_data, raw_clerk_data])

                if has_new_data:
                    save_bundle = {
                        "tax_raw_data": raw_tax_data,
                        "property_raw_data": cleaned_property_data or raw_property_data,
                        "clerk_raw_data": raw_clerk_data,
                        "county_links": final_links,
                        "source": "api_scrape_refresh"
                    }
                    
                    await asyncio.to_thread(
                        save_raw, request.county, request.county_parcel_id, save_bundle
                    )
                    logger.info(f"💾 DEBUG: Database updated successfully")
                else:
                    logger.info("💾 DEBUG: No fresh data scraped; skipping database update")
            
            # Send fresh data to client
            # For fresh data:
            logger.info(f"🔍 DEBUG: DataStandardizer input - FRESH:")
            if raw_tax_data:
                logger.info(f"   - raw_tax_data type: {type(raw_tax_data)}")
                logger.info(f"   - raw_tax_data keys: {list(raw_tax_data.keys())}")
                if 'current_tax' in raw_tax_data:
                    logger.info(f"   - raw_tax_data.current_tax: {raw_tax_data['current_tax']}")
                if 'general_info' in raw_tax_data:
                    logger.info(f"   - raw_tax_data.general_info: {raw_tax_data['general_info']}")
            else:
                logger.info(f"   - raw_tax_data: None")

            if raw_property_data:
                logger.info(f"   - raw_property_data type: {type(raw_property_data)}")
                logger.info(f"   - raw_property_data keys: {list(raw_property_data.keys())}")
                if 'owner_name' in raw_property_data:
                    logger.info(f"   - raw_property_data.owner_name: {raw_property_data['owner_name']}")
                if 'physical_address' in raw_property_data:
                    logger.info(f"   - raw_property_data.physical_address: {raw_property_data['physical_address']}")
            else:
                logger.info(f"   - raw_property_data: None")

            if raw_clerk_data:
                logger.info(f"   - raw_clerk_data type: {type(raw_clerk_data)}")
                logger.info(f"   - raw_clerk_data keys: {list(raw_clerk_data.keys())}")
                if 'records_count' in raw_clerk_data:
                    logger.info(f"   - raw_clerk_data.records_count: {raw_clerk_data['records_count']}")
            else:
                logger.info(f"   - raw_clerk_data: None")

            # Use final_links for response (includes merged additional links)
            response_links = final_links
            
            fresh_response = DataStandardizer.standardize_api_response(
                raw_tax_data, raw_property_data, raw_clerk_data,
                request.county,
                county_links=response_links
            )
            
            logger.info(f"🔍 DEBUG: Fresh scraped data summary:")
            logger.info(f"   - raw_tax_data: {type(raw_tax_data)} - {bool(raw_tax_data)}")
            logger.info(f"   - raw_property_data: {type(raw_property_data)} - {bool(raw_property_data)}")
            logger.info(f"   - raw_clerk_data: {type(raw_clerk_data)} - {bool(raw_clerk_data)}")

            logger.info(f"🔍 DEBUG: DataStandardizer fresh result:")
            logger.info(f"   - Response type: {type(fresh_response)}")
            logger.info(f"   - Has 'data' key: {'data' in fresh_response if isinstance(fresh_response, dict) else False}")
            if isinstance(fresh_response, dict) and 'data' in fresh_response:
                data_sample = str(fresh_response['data'])[:200]
                logger.info(f"   - Data sample: {data_sample}...")
            logger.info(f"🔍 DEBUG: About to send fresh response...")
            try:
                response_data = {'status': 'fresh', 'data': fresh_response['data']}
                response_json = json.dumps(response_data)
                logger.info(f"📤 DEBUG: Fresh response JSON length: {len(response_json)}")
                logger.info(f"📤 DEBUG: Fresh response sample: {response_json[:200]}...")
                yield f"data: {response_json}\n\n"
                logger.info(f"✅ DEBUG: Fresh response sent successfully")
            except Exception as e:
                logger.error(f"❌ DEBUG: Error sending fresh response: {e}")
            
            # Signal completion
            yield f"data: {json.dumps({'status': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"❌ DEBUG: Stream error: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002) 