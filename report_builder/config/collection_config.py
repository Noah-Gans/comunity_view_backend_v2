"""Collection configuration settings"""

import os
import json
from typing import List, Dict, Optional

class CollectionConfig:
    """Configuration for mass data collection"""
    
    def __init__(self):
        # Rate limiting settings
        self.requests_per_second = 1.2
        self.max_concurrent_requests = 15
        self.delay_between_requests = 1.0 / self.requests_per_second
        self.random_delay_range = (0.8, 1.2)  # Random jitter
        
        # Batch processing settings
        self.batch_size = 100  # Process parcels in batches
        self.max_retries = 3
        self.retry_delay = 5.0
        
        # File output settings
        self.output_directory = "output"  # Change from "scraped_data" to "output"
        self.file_formats = {
            "tax": "jsonl",
            "property": "jsonl", 
            "clerk": "jsonl"
        }
        
        # Counties to process (excluding teton_county_id)
        self.active_counties = [
            "fremont_county_wy",
            "lincoln_county_wy", 
            "sublette_county_wy",
            "teton_county_wy"  # Include Teton County Wyoming
        ]
        
        # GeoJSON file paths
        self.geojson_base_path = "geojsons"  # Local directory on VM
        self.geojson_file_pattern = "{county}/ownership_data_latest.geojson"  # Consistent filename
        
        self.gcs_bucket = "your-scraped-data-bucket"  # Where to upload results
        
        self.checkpoint_file = "collection_progress.json"
        
    def get_geojson_path(self, county: str) -> str:
        """Get the GeoJSON file path for a county"""
        return f"{self.geojson_base_path}/{self.geojson_file_pattern.format(county=county)}"
        
    def get_output_file_path(self, county: str, data_type: str) -> str:
        """Get output file path for a county and data type"""
        extension = self.file_formats.get(data_type, "jsonl")
        return f"{self.output_directory}/{county}_{data_type}_data.{extension}"

    def get_checkpoint_file_path(self) -> str:
        """Get the checkpoint file path"""
        return f"{self.output_directory}/{self.checkpoint_file}"

# Simple progress tracker
class CollectionProgress:
    """Tracks collection progress for restart capability"""
    
    def __init__(self, config: CollectionConfig):
        self.config = config
        self.progress_file = config.get_checkpoint_file_path()
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """Load existing progress"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def get_completed_count(self, county: str) -> int:
        """Get how many parcels have been completed for a county"""
        return self.progress.get(county, 0)
    
    def update_progress(self, county: str, completed_count: int):
        """Update progress for a county"""
        self.progress[county] = completed_count
        self._save_progress()
    
    def _save_progress(self):
        """Save progress to file"""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save progress: {e}")
