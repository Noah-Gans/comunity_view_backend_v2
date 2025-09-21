"""Collection configuration settings"""

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
        self.output_directory = "scraped_data"
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
        self.geojson_file_pattern = "{county}_data_files/{county}_final_ownership.geojson"
        
        self.gcs_bucket = "your-scraped-data-bucket"  # Where to upload results
        
    def get_geojson_path(self, county: str) -> str:
        """Get the GeoJSON file path for a county"""
        return f"{self.geojson_base_path}/{self.geojson_file_pattern.format(county=county)}"
        
    def get_output_file_path(self, county: str, data_type: str) -> str:
        """Get output file path for a county and data type"""
        extension = self.file_formats.get(data_type, "jsonl")
        return f"{self.output_directory}/{county}_{data_type}_data.{extension}"
