#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add the search_api directory to the Python path
sys.path.append(str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from search_engine import SearchEngine
from search_file_generator import create_search_index

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Property Search API",
    description="API for searching property ownership data across multiple counties",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize search engine (will be loaded in background)
search_engine = None

# Pydantic models for API responses
class SearchResult(BaseModel):
    GFI: str
    pidn: str
    owner: str
    mailing_address: str
    physical_address: str
    county: str
    state: str
    bbox: Optional[List[float]]
    clerk_rec: str
    property_det: str
    tax_info: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    search_time: str

class StatsResponse(BaseModel):
    total_entries: int
    counties: Dict[str, int]
    last_updated: Optional[str]

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Property Search API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "Search for properties",
            "/stats": "Get search index statistics",
            "/health": "Health check",
            "/reload": "Reload search index"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "search_index_loaded": search_engine is not None and search_engine.search_data is not None,
        "search_index_size": len(search_engine.search_data) if search_engine and search_engine.search_data else 0
    }

@app.get("/search", response_model=SearchResponse)
async def search_properties(
    q: str = Query(..., description="Search query"),
    limit: Optional[int] = Query(200, description="Maximum number of results to return"),
    counties: Optional[str] = Query(None, description="Comma-separated list of county codes"),
    lat: Optional[float] = Query(None, description="Latitude for spatial search priority"),
    lon: Optional[float] = Query(None, description="Longitude for spatial search priority"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to search in"),
    # New advanced search parameters
    is_advanced: bool = Query(False, description="Use advanced search mode"),
    search_fields: Optional[str] = Query(None, description="Comma-separated list of fields to search in advanced mode"),
    filters: Optional[str] = Query(None, description="JSON string of filters for advanced search"),
    sort_by: Optional[str] = Query(None, description="Field to sort by in advanced search"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc or desc")
):
    """
    Search for properties by owner name, address, parcel ID, etc.
    
    The search algorithm matches your frontend implementation:
    - Exact phrase matches get highest priority
    - All words matching gets moderate priority  
    - Partial word matches get lower priority
    - Results are filtered to only include relevant matches (score >= 300)
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    try:
        # Parse county filter (now expects county codes like teton_county_wy)
        county_filter = None
        if counties:
            county_filter = [county.strip() for county in counties.split(',') if county.strip()]
        
        # Parse field filter
        field_filter = None
        if fields:
            field_filter = [field.strip() for field in fields.split(',') if field.strip()]
        
        # Parse spatial parameters
        spatial_params = None
        if lat is not None and lon is not None:
            spatial_params = {"lat": lat, "lon": lon}
        
        # Parse advanced search parameters
        advanced_search_fields = None
        if search_fields:
            advanced_search_fields = [field.strip() for field in search_fields.split(',') if field.strip()]
        
        advanced_filters = None
        if filters:
            try:
                import json
                advanced_filters = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid filters JSON")
        
        advanced_sort = None
        if sort_by:
            advanced_sort = {"field": sort_by, "order": sort_order or "desc"}
        
        # Check if search engine is ready
        if search_engine is None:
            raise HTTPException(status_code=503, detail="Search engine is still initializing. Please try again in a moment.")
        
        # Perform search
        start_time = datetime.now()
        results = search_engine.search(
            q,
            limit=limit,
            county_filter=county_filter,
            field_filter=field_filter,
            spatial_params=spatial_params,
            is_advanced=is_advanced,
            search_fields=advanced_search_fields,
            filters=advanced_filters,
            sort_options=advanced_sort
        )
        search_duration = (datetime.now() - start_time).total_seconds()
        
        
        # Convert to response format with None safety
        search_results = []
        for result in results:
            search_results.append(SearchResult(
                GFI=result.get("GFI") or "",
                pidn=result.get("county_parcel_id") or "",
                owner=result.get("owner") or "",
                mailing_address=result.get("mail") or "",
                physical_address=result.get("physical") or "",
                county=result.get("county") or "",
                state=result.get("state") or "",
                bbox=result.get("bbox"),  # bbox can be None
                clerk_rec=result.get("clerk_rec") or "",
                property_det=result.get("property_det") or "",
                tax_info=result.get("tax_info") or ""
            ))
        
        return SearchResponse(
            query=q,
            results=search_results,
            total_results=len(search_results),
            search_time=f"{search_duration:.3f}s"
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.get("/stats", response_model=StatsResponse)
async def get_search_stats():
    """Get statistics about the search index"""
    try:
        if search_engine is None:
            raise HTTPException(status_code=503, detail="Search engine is still initializing. Please try again in a moment.")
        stats = search_engine.get_search_stats()
        
        # Check if search index file exists and get its modification time
        last_updated = None
        search_index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_index.json")
        if os.path.exists(search_index_path):
            mtime = os.path.getmtime(search_index_path)
            last_updated = datetime.fromtimestamp(mtime).isoformat()
        
        return StatsResponse(
            total_entries=stats["total_entries"],
            counties=stats["counties"],
            last_updated=last_updated
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@app.post("/reload")
async def reload_search_index():
    """Reload the search index from file"""
    try:
        if search_engine is None:
            raise HTTPException(status_code=503, detail="Search engine is still initializing. Please try again in a moment.")
        search_engine.reload_search_data()
        return {
            "message": "Search index reloaded successfully",
            "total_entries": len(search_engine.search_data) if search_engine.search_data else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Reload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload search index")

@app.post("/generate-search-index")
async def generate_search_index():
    """Generate a new search index from county data files"""
    try:
        # Change to the search_api directory to run the generator
        original_cwd = os.getcwd()
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Generate the search index
        search_index_path = create_search_index()
        
        # Change back to original directory
        os.chdir(original_cwd)
        
        if search_index_path and os.path.exists(search_index_path):
            # Reload the search engine with new data
            global search_engine
            if search_engine is None:
                search_engine = SearchEngine()
            else:
                search_engine.reload_search_data()
            
            return {
                "message": "Search index generated successfully",
                "file_path": search_index_path,
                "total_entries": len(search_engine.search_data) if search_engine.search_data else 0,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate search index")
            
    except Exception as e:
        logger.error(f"Generate search index error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate search index: {str(e)}")

@app.post("/internal/reload-search-index")
async def reload_search_index():
    """
    Internal endpoint to reload the search index after updates
    """
    try:
        global search_engine
        if search_engine is None:
            search_engine = SearchEngine()
        else:
            logger.info("🔄 Reloading search index...")
            search_engine.reload_search_data()
        
        return {
            "status": "success",
            "message": "Search index reloaded successfully",
            "total_entries": len(search_engine.search_data) if search_engine.search_data else 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Reload search index error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload search index: {str(e)}")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the search engine on startup"""
    global search_engine
    logger.info("🚀 Starting Property Search API...")
    
    # Check if search index exists
    search_index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_index.json")
    if not os.path.exists(search_index_path):
        logger.warning("⚠️  Search index not found. Run /generate-search-index to create it.")
        search_engine = SearchEngine()
    else:
        logger.info("📦 Loading search index (this may take a moment)...")
        # Initialize search engine in background
        import asyncio
        loop = asyncio.get_event_loop()
        search_engine = await loop.run_in_executor(None, SearchEngine)
        logger.info("✅ Search index loaded successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 