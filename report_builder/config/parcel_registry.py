"""Parcel registry - extracts parcel IDs from GeoJSON files"""

import json
import os
from typing import List, Dict, Optional
from .collection_config import CollectionConfig

class ParcelRegistry:
    """Manages parcel IDs from GeoJSON files"""
    
    def __init__(self):
        self.config = CollectionConfig()
        self._parcel_cache = {}
        
    def get_parcels_for_county(self, county: str, max_parcels: Optional[int] = None) -> List[Dict]:
        """Get all parcels for a county from GeoJSON file"""
        if county in self._parcel_cache:
            parcels = self._parcel_cache[county]
        else:
            parcels = self._load_parcels_from_geojson(county)
            self._parcel_cache[county] = parcels
            
        # Filter out parcels without required keys
        valid_parcels = []
        for parcel in parcels:
            # Skip if no property_details_key and no tax_details_key
            if not parcel.get("property_details_key") and not parcel.get("tax_details_key"):
                continue
                
            valid_parcels.append(parcel)
        
        # Limit for testing if requested
        if max_parcels:
            valid_parcels = valid_parcels[:max_parcels]
            
        return valid_parcels
    
    def _load_parcels_from_geojson(self, county: str) -> List[Dict]:
        """Load parcels from GeoJSON file"""
        geojson_path = self.config.get_geojson_path(county)
        
        if not os.path.exists(geojson_path):
            print(f"Warning: GeoJSON file not found: {geojson_path}")
            return []
            
        try:
            print(f"Loading parcels from {geojson_path}")
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
                
            parcels = []
            for feature in geojson_data.get("features", []):
                properties = feature.get("properties", {})
                
                # Extract the keys we need for scraping
                parcel_info = {
                    "county": county,
                    "county_parcel_id": properties.get("county_parcel_id"),
                    "property_details_key": properties.get("property_details_key"),
                    "tax_details_key": properties.get("tax_details_key"),
                    "clerk_records_key": properties.get("clerk_records_key"),
                    "owner_name": properties.get("owner_name"),
                    "physical_address": properties.get("physical"),
                    "acres": properties.get("acre")
                }
                
                parcels.append(parcel_info)
                
            print(f"Loaded {len(parcels)} parcels for {county}")
            return parcels
            
        except Exception as e:
            print(f"Error loading GeoJSON for {county}: {e}")
            return []
    
    def get_total_parcel_count(self) -> Dict[str, int]:
        """Get total parcel counts for all counties"""
        counts = {}
        for county in self.config.active_counties:
            parcels = self.get_parcels_for_county(county)
            counts[county] = len(parcels)
        return counts
