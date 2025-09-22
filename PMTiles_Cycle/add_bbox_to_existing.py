#!/usr/bin/env python3
"""
Add bbox data to existing standardized GeoJSON files
"""

import json
import os
from pathlib import Path
from downloading_and_geojson_processing.data_standardizer import DataStandardizer

def add_bbox_to_file(file_path):
    """Add bbox to an existing standardized GeoJSON file"""
    
    print(f"🔄 Processing {file_path}")
    
    # Load the existing data
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Initialize standardizer for bbox calculation
    standardizer = DataStandardizer()
    
    # Add bbox to each feature
    features_updated = 0
    for feature in data.get('features', []):
        geometry = feature.get('geometry')
        if geometry:
            # Calculate bbox for this feature
            bbox = standardizer._calculate_feature_bbox(geometry)
            if bbox:
                feature['properties']['bbox'] = bbox
                features_updated += 1
    
    print(f"  ✅ Added bbox to {features_updated} features")
    
    # Save the updated data
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"  💾 Saved updated file: {file_path}")
    return features_updated

def main():
    """Main function to add bbox to existing files"""
    
    print("🚀 Adding Bbox to Existing Standardized Data")
    print("=" * 50)
    
    # Path to the data directory
    data_dir = Path("geojsons_for_db_upload")
    
    if not data_dir.exists():
        print("❌ Data directory not found")
        return
    
    total_features_updated = 0
    
    # Process each county directory
    for county_dir in data_dir.iterdir():
        if county_dir.is_dir() and county_dir.name.endswith('_data_files'):
            county_name = county_dir.name.replace('_data_files', '')
            geojson_file = county_dir / f"{county_name}_final_ownership.geojson"
            
            if geojson_file.exists():
                print(f"\n📂 Processing {county_name}...")
                try:
                    features_updated = add_bbox_to_file(geojson_file)
                    total_features_updated += features_updated
                except Exception as e:
                    print(f"  ❌ Error processing {county_name}: {e}")
            else:
                print(f"  ⚠️  No final ownership file found for {county_name}")
    
    print(f"\n🎉 Bbox addition complete!")
    print(f"📊 Total features updated: {total_features_updated}")

if __name__ == "__main__":
    main()
