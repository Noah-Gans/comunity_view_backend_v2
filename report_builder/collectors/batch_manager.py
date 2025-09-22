"""Batch manager for processing parcels with rate limiting"""

import asyncio
import time
import random
from typing import List, Dict
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.api_wrapper import APIWrapper
from scheduling.rate_limiter import RateLimiter
from config.collection_config import CollectionConfig

class BatchManager:
    """Manages batch processing of parcels with rate limiting"""
    
    def __init__(self):
        self.config = CollectionConfig()
        self.api_wrapper = APIWrapper()
        self.rate_limiter = RateLimiter(
            requests_per_second=self.config.requests_per_second
        )  # Only pass requests_per_second
        
    async def process_county_parcels(self, county: str, parcels: List[Dict], 
                                file_manager, progress_tracker, logger,
                                progress_manager=None):
        """Process all parcels for a county with progress tracking"""
        
        # Create semaphore for this county
        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        # Create tasks for all parcels
        tasks = []
        for i, parcel in enumerate(parcels):
            task = self._process_single_parcel_with_semaphore(
                semaphore, county, parcel, file_manager, progress_tracker, logger, progress_manager
            )
            tasks.append(task)
        
        # Process all parcels
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Remove this line - progress is now updated per parcel
        # if progress_manager:
        #     progress_manager.update_progress(county, len(parcels))
        
        # Count successes and failures
        successes = sum(1 for r in results if isinstance(r, dict) and not r.get("error"))
        failures = len(results) - successes
        
        logger.info(f"County {county} complete: {successes} successful, {failures} failed")
        
        return results
    
    async def _process_single_parcel_with_semaphore(self, semaphore, county: str, 
                                                   parcel: Dict, file_manager, 
                                                   progress_tracker, logger, progress_manager=None):
        """Process a single parcel with semaphore for concurrency control"""
        
        async with semaphore:
            # Rate limiting delay
            await self.rate_limiter.wait()
            
            try:
                # Collect data for this parcel
                result = await self.api_wrapper.collect_parcel_data(county, parcel)
                result["collection_timestamp"] = datetime.now().isoformat()
                
                # Write to appropriate files
                await file_manager.write_parcel_data(county, result)
                
                # Update progress immediately after successful processing
                if progress_manager and not result.get("error"):
                    current_progress = progress_manager.get_completed_count(county)
                    progress_manager.update_progress(county, current_progress + 1)
                
                # Update progress tracker
                progress_tracker.increment_completed()
                
                if result.get("errors"):
                    logger.warning(f"Parcel {parcel.get('property_details_key', 'unknown')} had errors: {result['errors']}")
                
                return result
                
            except Exception as e:
                error_msg = f"Failed to process parcel {parcel.get('property_details_key', 'unknown')}: {e}"
                logger.error(error_msg)
                progress_tracker.increment_failed()
                
                return {"error": error_msg, "parcel": parcel}