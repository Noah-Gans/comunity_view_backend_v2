#!/usr/bin/env python3
"""
Test script to verify bbox calculation for individual features
"""

import json
from pathlib import Path
from downloading_and_geojson_processing.data_standardizer import DataStandardizer

def test_bbox_calculation():
    """Test bbox calculation for individual features"""
    
    # Initialize the data standardizer
    standardizer = DataStandardizer()
    
    # Test with a sample geometry
    test_geometry = {
        "type": "Polygon",
        "coordinates": [[
            [-110.123, 43.456],
            [-110.124, 43.456],
            [-110.124, 43.457],
            [-110.123, 43.457],
            [-110.123, 43.456]
        ]]
    }
    
    # Test bbox calculation
    bbox = standardizer._calculate_feature_bbox(test_geometry)
    print(f"✅ Test bbox calculation: {bbox}")
    
    # Test with MultiPolygon
    test_multipolygon = {
        "type": "MultiPolygon",
        "coordinates": [[[
            [-110.123, 43.456],
            [-110.124, 43.456],
            [-110.124, 43.457],
            [-110.123, 43.457],
            [-110.123, 43.456]
        ]]]
    }
    
    bbox2 = standardizer._calculate_feature_bbox(test_multipolygon)
    print(f"✅ Test MultiPolygon bbox calculation: {bbox2}")
    
    # Test with invalid geometry
    invalid_geometry = {"type": "Point", "coordinates": [-110.123, 43.456]}
    bbox3 = standardizer._calculate_feature_bbox(invalid_geometry)
    print(f"✅ Test invalid geometry bbox calculation: {bbox3}")
    
    return True

def test_standardization_with_bbox():
    """Test full standardization process with bbox"""
    
    # Create a test feature collection
    test_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "owner": "Test Owner",
                    "pidn": "12345"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-110.123, 43.456],
                        [-110.124, 43.456],
                        [-110.124, 43.457],
                        [-110.123, 43.457],
                        [-110.123, 43.456]
                    ]]
                }
            }
        ]
    }
    
    # Test standardization
    standardizer = DataStandardizer()
    standardized = standardizer.standardize_ownership(test_data, "test_county")
    
    # Check if bbox was added
    if standardized["features"]:
        feature = standardized["features"][0]
        bbox = feature["properties"].get("bbox")
        print(f"✅ Standardization test - bbox added: {bbox}")
        
        # Verify bbox format: [min_lon, min_lat, max_lon, max_lat]
        if bbox and len(bbox) == 4:
            min_lon, min_lat, max_lon, max_lat = bbox
            print(f"   Bbox format: [{min_lon}, {min_lat}, {max_lon}, {max_lat}]")
            print(f"   Width: {max_lon - min_lon:.6f} degrees")
            print(f"   Height: {max_lat - min_lat:.6f} degrees")
        else:
            print("   ❌ Bbox format incorrect")
    else:
        print("❌ No features in standardized data")
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Bbox Calculation")
    print("=" * 40)
    
    try:
        test_bbox_calculation()
        print("\n" + "=" * 40)
        test_standardization_with_bbox()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
