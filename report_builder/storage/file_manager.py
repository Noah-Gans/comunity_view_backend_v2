"""File manager for writing scraped data to organized files"""

import json
import os
import asyncio
from typing import Dict
from datetime import datetime

class FileManager:
    """Manages writing scraped data to separate files by county and data type"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.file_handles = {}
        self.write_locks = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
    def initialize_county_files(self, county: str):
        """Initialize output files for a county"""
        
        data_types = ["tax", "property", "clerk"]
        
        for data_type in data_types:
            file_path = os.path.join(self.output_dir, f"{county}_{data_type}_data.jsonl")
            
            # Create file and write header
            with open(file_path, 'w') as f:
                header = {
                    "file_type": f"{county}_{data_type}_data",
                    "created_at": datetime.now().isoformat(),
                    "county": county,
                    "data_type": data_type,
                    "description": f"Mass collected {data_type} data for {county}"
                }
                f.write(json.dumps(header) + "\n")
                
            # Create lock for thread-safe writing
            lock_key = f"{county}_{data_type}"
            self.write_locks[lock_key] = asyncio.Lock()
            
        print(f"Initialized output files for {county}")
    
    async def write_parcel_data(self, county: str, parcel_data: Dict):
        """Write parcel data to appropriate files"""
        
        scraped_data = parcel_data.get("scraped_data", {})
        
        # Write tax data
        if "tax_data" in scraped_data:
            await self._write_to_file(county, "tax", {
                "parcel_id": parcel_data.get("parcel_id"),
                "property_details_key": parcel_data.get("property_details_key"),
                "tax_details_key": parcel_data.get("tax_details_key"),
                "collection_timestamp": parcel_data.get("collection_timestamp"),
                "tax_data": scraped_data["tax_data"]
            })
        
        # Write property data
        if "property_data" in scraped_data:
            await self._write_to_file(county, "property", {
                "parcel_id": parcel_data.get("parcel_id"),
                "property_details_key": parcel_data.get("property_details_key"),
                "tax_details_key": parcel_data.get("tax_details_key"),
                "collection_timestamp": parcel_data.get("collection_timestamp"),
                "property_data": scraped_data["property_data"]
            })
        
        # Write clerk data
        if "clerk_data" in scraped_data:
            await self._write_to_file(county, "clerk", {
                "parcel_id": parcel_data.get("parcel_id"),
                "property_details_key": parcel_data.get("property_details_key"),
                "clerk_records_key": parcel_data.get("clerk_records_key"),
                "collection_timestamp": parcel_data.get("collection_timestamp"),
                "clerk_data": scraped_data["clerk_data"]
            })
    
    async def _write_to_file(self, county: str, data_type: str, data: Dict):
        """Write data to a specific file with thread safety"""
        
        lock_key = f"{county}_{data_type}"
        file_path = os.path.join(self.output_dir, f"{county}_{data_type}_data.jsonl")
        
        # Use lock to ensure thread-safe writing
        if lock_key in self.write_locks:
            async with self.write_locks[lock_key]:
                with open(file_path, 'a') as f:
                    f.write(json.dumps(data) + "\n")
        else:
            # Fallback if lock not initialized
            with open(file_path, 'a') as f:
                f.write(json.dumps(data) + "\n")
    
    def get_file_stats(self) -> Dict[str, int]:
        """Get statistics about written files"""
        stats = {}
        
        for filename in os.listdir(self.output_dir):
            if filename.endswith('.jsonl'):
                file_path = os.path.join(self.output_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        line_count = sum(1 for _ in f) - 1  # Subtract header line
                    stats[filename] = line_count
                except:
                    stats[filename] = 0
                    
        return stats
