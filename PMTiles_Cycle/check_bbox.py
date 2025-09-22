#!/usr/bin/env python3
"""
Check bbox values in standardized data
"""

import json

def check_bbox_values():
    """Check bbox values in the standardized data"""
    
    # Load the standardized data
    with open('geojsons_for_db_upload/teton_county_wy_data_files/teton_county_wy_final_ownership.geojson', 'r') as f:
        data = json.load(f)
    
    print(f"✅ Loaded data with {len(data['features'])} features")
    
    # Check first few features
    features = data['features']
    bbox_count = 0
    none_count = 0
    
    print("\n🔍 Checking bbox values in first 10 features...")
    for i, feature in enumerate(features[:10]):
        bbox = feature['properties'].get('bbox')
        if bbox:
            bbox_count += 1
            print(f"  Feature {i}: bbox = {bbox}")
        else:
            none_count += 1
            print(f"  Feature {i}: bbox = None")
    
    print(f"\n📊 Summary: {bbox_count} with bbox, {none_count} without bbox")
    
    # Check if any features have bbox
    total_with_bbox = sum(1 for f in features if f['properties'].get('bbox'))
    print(f"📊 Total features with bbox: {total_with_bbox}/{len(features)}")
    
    # Check a sample feature's geometry
    if features:
        sample = features[0]
        geometry = sample.get('geometry')
        print(f"\n🔍 Sample feature geometry type: {geometry.get('type') if geometry else 'None'}")
        if geometry and 'coordinates' in geometry:
            coords = geometry['coordinates']
            print(f"  First coordinate: {coords[0][0] if coords and coords[0] else 'None'}")

if __name__ == "__main__":
    check_bbox_values()
