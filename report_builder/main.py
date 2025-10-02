#!/usr/bin/env python3
"""
Report Builder - Mass Property Data Collection System
Collects property data from all counties and stores in organized files.
"""

import asyncio
import json
import time
import sys
import os
from pathlib import Path

# Add property_info_api to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'property_info_api'))

from config.collection_config import CollectionConfig, CollectionProgress
from config.parcel_registry import ParcelRegistry
from collectors.batch_manager import BatchManager
from storage.file_manager import FileManager
from monitoring.progress_tracker import ProgressTracker
from monitoring.collection_logger import CollectionLogger
from download_geojsons import download_geojsons_from_gcs

class ReportBuilderMain:
    def __init__(self):
        self.config = CollectionConfig()
        self.progress_manager = CollectionProgress(self.config)
        self.parcel_registry = ParcelRegistry(self.progress_manager)
        self.batch_manager = BatchManager()
        self.file_manager = FileManager()
        self.progress_tracker = ProgressTracker()
        self.logger = CollectionLogger()
        
    async def run_collection(self, counties=None, max_parcels_per_county=None, resume=False, data_types=None):
        """Run the complete collection process"""
        self.logger.info(f"Starting mass property data collection for data types: {data_types}")
        
        # Get counties to process (skip teton_county_id)
        if counties is None:
            counties = self.config.active_counties
        
        # Set default data types if not specified
        if data_types is None:
            data_types = ["tax", "property", "clerk"]
        
        total_parcels = 0
        for county in counties:
            parcels = self.parcel_registry.get_parcels_for_county(
                county, max_parcels_per_county, 
                progress_manager=self.progress_manager if resume else None
            )
            total_parcels += len(parcels)
            self.logger.info(f"County {county}: {len(parcels)} parcels to process")
        
        self.progress_tracker.initialize(total_parcels)
        
        # Process all counties in parallel, each with their own semaphore
        county_tasks = []
        for county in counties:
            self.logger.info(f"Starting collection for {county}")
            task = self.process_county(county, max_parcels_per_county, data_types)
            county_tasks.append(task)
        
        # Run all counties at the same time
        self.logger.info(f"Processing {len(counties)} counties in parallel")
        await asyncio.gather(*county_tasks)
            
        self.logger.info("Collection complete!")
        self.progress_tracker.print_final_summary()
    
    async def process_county(self, county: str, max_parcels_per_county=None, data_types=None):
        """Process all parcels for a single county"""
        
        # Get parcels for this county
        parcels = self.parcel_registry.get_parcels_for_county(
            county, max_parcels_per_county, progress_manager=self.progress_manager
        )
        
        if not parcels:
            self.logger.warning(f"No parcels found for {county}")
            return
            
        # Initialize output files for this county
        self.file_manager.initialize_county_files(county)
        
        # Process parcels in batches
        await self.batch_manager.process_county_parcels(
            county, parcels, self.file_manager, self.progress_tracker, self.logger,
            progress_manager=self.progress_manager,
            data_types=data_types
        )

def get_site_group(county: str, data_type: str, url: str) -> str:
    """Route request to correct semaphore based on county/data_type/URL"""
    
    # Tyler Technologies tax system
    if data_type == "tax" and county in ["lincoln_county_wy", "fremont_county_wy", "sublette_county_wy"]:
        return "tyler_tech_tax"
    
    # Teton County unified system  
    elif county == "teton_county_wy":
        return "teton_wy_all"
    
    # Lincoln County property details
    elif data_type == "property" and county == "lincoln_county_wy":
        return "lincoln_property"
        
    # Greenwood property system
    elif data_type == "property" and county in ["fremont_county_wy", "sublette_county_wy"]:
        return "greenwood_property"
        
    # Clerk systems
    elif data_type == "clerk":
        return "clerk_systems"
        
    else:
        return "default"

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Mass Property Data Collection")
    parser.add_argument("--counties", nargs="+", help="Counties to process", 
                       default=["fremont_county_wy", "lincoln_county_wy", "sublette_county_wy", "teton_county_wy"])
    parser.add_argument("--max-parcels", type=int, help="Max parcels per county (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without actual scraping")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--download-geojsons", action="store_true", help="Download latest GeoJSONs from GCS first")
    
    # NEW: Add data type selection
    parser.add_argument("--data-types", nargs="+", choices=["tax", "property", "clerk"], 
                       help="Data types to collect (default: all)", default=["tax", "property", "clerk"])
    
    args = parser.parse_args()
    
    # Download GeoJSONs if requested
    if args.download_geojsons:
        from download_latest_geojsons import download_latest_geojsons
        download_latest_geojsons()
    
    main = ReportBuilderMain()
    asyncio.run(main.run_collection(args.counties, args.max_parcels, args.resume, args.data_types))
