#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import sys
import os
import logging
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path to access shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from shared.database.storage.db import init_db, get_latest_raw

# Import data standardizer from local directory
from data_standardizer import DataStandardizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Report Builder API",
    description="Batch retrieval of cached property data for report generation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "1000"))  # Limit batch size
MAX_CONCURRENT_DB_QUERIES = int(os.getenv("MAX_CONCURRENT_DB_QUERIES", "50"))  # Concurrent DB queries

# Create thread pool for database operations
db_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DB_QUERIES, thread_name_prefix="db_query")

# Pydantic models
class ParcelIdentifier(BaseModel):
    county: str
    county_parcel_id: str

class BatchRequest(BaseModel):
    parcels: List[ParcelIdentifier] = Field(..., max_length=MAX_BATCH_SIZE)

class ParcelData(BaseModel):
    county: str
    county_parcel_id: str
    found: bool
    general_info: Optional[Dict[str, Any]] = None
    tax_data: Optional[Dict[str, Any]] = None
    property_data: Optional[Dict[str, Any]] = None
    clerk_data: Optional[Dict[str, Any]] = None
    collected_at: Optional[str] = None

class BatchResponse(BaseModel):
    total_requested: int
    total_found: int
    total_missing: int
    parcels: List[ParcelData]
    processing_time_ms: float

@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    init_db()
    logger.info("🚀 Report Builder API started")
    logger.info(f"📊 Database location: {os.path.join(os.path.dirname(__file__), '../..', 'shared', 'database', 'storage', 'property_data.db')}")
    logger.info(f"⚙️  Configuration: max_batch_size={MAX_BATCH_SIZE}, max_concurrent_queries={MAX_CONCURRENT_DB_QUERIES}")

@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    db_executor.shutdown(wait=True)
    logger.info("🛑 Report Builder API shutdown complete")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Report Builder API",
        "version": "1.0.0",
        "description": "Batch retrieval of cached property data",
        "endpoints": {
            "/batch-retrieve": "POST - Retrieve cached data for multiple parcels",
            "/health": "GET - Health check",
            "/stats": "GET - Get database statistics"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "report_builder_api",
        "timestamp": datetime.now().isoformat()
    }

async def process_parcel(parcel: ParcelIdentifier) -> ParcelData:
    """Process a single parcel asynchronously"""
    try:
        # Query database in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        raw_data = await loop.run_in_executor(
            db_executor,
            get_latest_raw,
            parcel.county,
            parcel.county_parcel_id
        )
        
        if not raw_data:
            return ParcelData(
                county=parcel.county,
                county_parcel_id=parcel.county_parcel_id,
                found=False
            )
        
        # Extract data from nested structure
        tax_data = None
        if raw_data.get("tax_raw_data"):
            tax_section = raw_data["tax_raw_data"]
            if isinstance(tax_section, dict):
                tax_data = tax_section.get("tax_data", tax_section)
        
        property_data = None
        if raw_data.get("property_raw_data"):
            prop_section = raw_data["property_raw_data"]
            if isinstance(prop_section, dict):
                property_data = prop_section.get("property_data", prop_section)
        
        clerk_data = None
        if raw_data.get("clerk_raw_data"):
            clerk_section = raw_data["clerk_raw_data"]
            if isinstance(clerk_section, dict):
                clerk_data = clerk_section.get("clerk_data", clerk_section)
        
        # Standardize data using DataStandardizer
        try:
            standardized_response = DataStandardizer.standardize_api_response(
                tax_data=tax_data,
                property_data=property_data,
                clerk_data=clerk_data,
                county=parcel.county,
                county_links=raw_data.get("county_links")
            )
            
            return ParcelData(
                county=parcel.county,
                county_parcel_id=parcel.county_parcel_id,
                found=True,
                general_info=standardized_response.get("data", {}).get("general_info"),
                tax_data=standardized_response.get("data", {}).get("tax"),
                property_data=standardized_response.get("data", {}).get("property_details"),
                clerk_data=standardized_response.get("data", {}).get("clerk"),
                collected_at=raw_data.get("collected_at")
            )
        except Exception as std_error:
            logger.error(f"Error standardizing data for {parcel.county}/{parcel.county_parcel_id}: {std_error}")
            # Fallback to raw data
            return ParcelData(
                county=parcel.county,
                county_parcel_id=parcel.county_parcel_id,
                found=True,
                general_info=None,
                tax_data=tax_data,
                property_data=property_data,
                clerk_data=clerk_data,
                collected_at=raw_data.get("collected_at")
            )
        
    except Exception as e:
        logger.error(f"Error retrieving {parcel.county}/{parcel.county_parcel_id}: {e}")
        return ParcelData(
            county=parcel.county,
            county_parcel_id=parcel.county_parcel_id,
            found=False
        )

@app.post("/batch-retrieve", response_model=BatchResponse)
async def batch_retrieve(request: BatchRequest):
    """
    Retrieve cached data for multiple parcels.
    Fast bulk lookup - no scraping, only returns what's in the database.
    
    Supports concurrent processing with automatic request size limiting.
    Max batch size: 1000 parcels (configurable via MAX_BATCH_SIZE env var)
    
    Request body:
    {
        "parcels": [
            {"county": "teton_county_wy", "county_parcel_id": "22-41-17-22-1-01-020"},
            {"county": "lincoln_county_wy", "county_parcel_id": "L0009876"}
        ]
    }
    
    Returns detailed property data for each parcel that exists in the cache.
    """
    start_time = datetime.now()
    
    if not request.parcels:
        raise HTTPException(status_code=400, detail="No parcels provided")
    
    # Check batch size
    if len(request.parcels) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Batch size {len(request.parcels)} exceeds maximum of {MAX_BATCH_SIZE} parcels"
        )
    
    logger.info(f"📦 Batch request for {len(request.parcels)} parcels")
    
    # Process all parcels concurrently with semaphore to limit database connections
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DB_QUERIES)
    
    async def process_with_semaphore(parcel):
        async with semaphore:
            return await process_parcel(parcel)
    
    # Create tasks for all parcels
    tasks = [process_with_semaphore(parcel) for parcel in request.parcels]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=False)
    
    # Count successful retrievals
    found_count = sum(1 for result in results if result.found)
    
    # Calculate processing time
    processing_time = (datetime.now() - start_time).total_seconds() * 1000
    
    logger.info(f"✅ Batch complete: {found_count}/{len(request.parcels)} found in {processing_time:.2f}ms")
    
    return BatchResponse(
        total_requested=len(request.parcels),
        total_found=found_count,
        total_missing=len(request.parcels) - found_count,
        parcels=results,
        processing_time_ms=round(processing_time, 2)
    )

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    try:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), '../..', 'shared', 'database', 'storage', 'property_data.db')
        
        with sqlite3.connect(db_path) as conn:
            # Get total records
            cursor = conn.execute("SELECT COUNT(*) FROM property_raw")
            total_records = cursor.fetchone()[0]
            
            # Get unique parcels
            cursor = conn.execute("SELECT COUNT(DISTINCT county || '-' || county_parcel_id) FROM property_raw")
            unique_parcels = cursor.fetchone()[0]
            
            # Get records by county
            cursor = conn.execute("SELECT county, COUNT(DISTINCT county_parcel_id) FROM property_raw GROUP BY county")
            by_county = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_records": total_records,
            "unique_parcels": unique_parcels,
            "parcels_by_county": by_county,
            "database_path": db_path
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9003, log_level="info")
