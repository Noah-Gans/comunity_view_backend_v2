#!/usr/bin/env python3
"""
Comprehensive Search API Test - Demonstrates all new features
"""

from search_engine import SearchEngine
import json

def test_search_features():
    """Test all search features with various queries"""
    
    # Initialize search engine
    engine = SearchEngine()
    print("✅ Search engine loaded")
    print(f"📊 Total entries in index: {len(engine.search_data)}")
    
    # Test queries
    test_queries = [
        "ladd",
        "smith", 
        "teton",
        "wy",
        "22-41",
        "RPA001",
        "PO BOX"
    ]
    
    print("\n" + "="*80)
    print("🔍 TESTING BASIC SEARCH (ALL FIELDS)")
    print("="*80)
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        results = engine.search(query)
        # Limit results manually for display
        display_results = results[:5]
        print(f"   📊 Results: {len(results)} (showing first 5)")
        if display_results:
            print(f"   🎯 Sample result:")
            sample = display_results[0]
            print(f"      Owner: {sample.get('owner', 'N/A')}")
            print(f"      PIDN: {sample.get('pidn', 'N/A')}")
            print(f"      County: {sample.get('county', 'N/A')}, {sample.get('state', 'N/A')}")
    
    print("\n" + "="*80)
    print("🏛️ TESTING COUNTY FILTERING (COUNTY CODES)")
    print("="*80)
    
    county_tests = [
        (["teton_county_wy"], "Teton County WY only"),
        (["teton_county_id"], "Teton County ID only"),
        (["teton_county_wy", "teton_county_id"], "Both Teton counties"),
        (["lincoln_county_wy"], "Lincoln County WY only")
    ]
    
    for counties, description in county_tests:
        print(f"\n📝 {description}: {counties}")
        results = engine.search("ladd", county_filter=counties)
        # Limit results manually for display
        display_results = results[:3]
        print(f"   📊 Results: {len(results)} (showing first 3)")
        if display_results:
            print(f"   🎯 Sample result:")
            sample = display_results[0]
            print(f"      UID: {sample.get('global_parcel_uid', 'N/A')}")
            print(f"      Owner: {sample.get('owner', 'N/A')}")
    
    print("\n" + "="*80)
    print("🎯 TESTING FIELD-SPECIFIC SEARCH")
    print("="*80)
    
    field_tests = [
        (["owner"], "Owner field only"),
        (["pidn"], "Parcel ID field only"),
        (["mailing_address"], "Mailing address field only"),
        (["physical_address"], "Physical address field only"),
        (["county"], "County field only"),
        (["owner", "pidn"], "Owner OR Parcel ID"),
        (["mailing_address", "physical_address"], "Either address field")
    ]
    
    for fields, description in field_tests:
        print(f"\n📝 {description}: {fields}")
        results = engine.search("ladd", field_filter=fields)
        # Limit results manually for display
        display_results = results[:3]
        print(f"   📊 Results: {len(results)} (showing first 3)")
        if display_results:
            print(f"   🎯 Sample result:")
            sample = display_results[0]
            if "owner" in fields:
                print(f"      Owner: {sample.get('owner', 'N/A')}")
            if "pidn" in fields:
                print(f"      PIDN: {sample.get('pidn', 'N/A')}")
            if "mailing_address" in fields:
                print(f"      Mailing: {sample.get('mailing_address', 'N/A')}")
    
    print("\n" + "="*80)
    print("🗺️ TESTING SPATIAL SEARCH (PROXIMITY)")
    print("="*80)
    
    spatial_tests = [
        (43.5, -110.2, "Teton County area"),
        (42.8, -108.7, "Fremont County area"),
        (43.0, -110.0, "Central Teton area")
    ]
    
    for lat, lon, description in spatial_tests:
        print(f"\n📝 {description}: lat={lat}, lon={lon}")
        results = engine.search("ladd", spatial_params={"lat": lat, "lon": lon})
        # Limit results manually for display
        display_results = results[:3]
        print(f"   📊 Results: {len(results)} (showing first 3)")
        if display_results:
            print(f"   🎯 Sample result:")
            sample = display_results[0]
            bbox = sample.get('bbox')
            if bbox:
                center_lon = (bbox[0] + bbox[2]) / 2
                center_lat = (bbox[1] + bbox[3]) / 2
                distance = ((center_lon - lon) ** 2 + (center_lat - lat) ** 2) ** 0.5
                print(f"      Distance: {distance:.4f} degrees")
            print(f"      Owner: {sample.get('owner', 'N/A')}")
    
    print("\n" + "="*80)
    print("🔗 TESTING COMBINED FILTERS")
    print("="*80)
    
    combined_tests = [
        {
            "query": "ladd",
            "counties": ["teton_county_wy"],
            "fields": ["owner"],
            "spatial": {"lat": 43.5, "lon": -110.2},
            "description": "Teton WY + Owner field + Spatial proximity"
        },
        {
            "query": "smith",
            "counties": ["teton_county_id"],
            "fields": ["pidn", "mailing_address"],
            "description": "Teton ID + PIDN or Address fields"
        }
    ]
    
    for test in combined_tests:
        print(f"\n📝 {test['description']}")
        print(f"   Query: '{test['query']}'")
        print(f"   Counties: {test.get('counties', 'None')}")
        print(f"   Fields: {test.get('fields', 'None')}")
        if 'spatial' in test:
            print(f"   Spatial: lat={test['spatial']['lat']}, lon={test['spatial']['lon']}")
        
        results = engine.search(
            test['query'],
            county_filter=test.get('counties'),
            field_filter=test.get('fields'),
            spatial_params=test.get('spatial')
        )
        # Limit results manually for display
        display_results = results[:3]
        print(f"   📊 Results: {len(results)} (showing first 3)")
        if display_results:
            print(f"   🎯 Sample result:")
            sample = display_results[0]
            print(f"      UID: {sample.get('global_parcel_uid', 'N/A')}")
            print(f"      Owner: {sample.get('owner', 'N/A')}")
    
    print("\n" + "="*80)
    print("📊 PERFORMANCE TEST")
    print("="*80)
    
    import time
    
    # Test search speed
    test_query = "ladd"
    print(f"\n📝 Testing search speed for: '{test_query}'")
    
    # Basic search
    start_time = time.time()
    basic_results = engine.search(test_query)
    basic_time = (time.time() - start_time) * 1000
    
    # County filtered search
    start_time = time.time()
    county_results = engine.search(test_query, county_filter=["teton_county_wy"])
    county_time = (time.time() - start_time) * 1000
    
    # Field filtered search
    start_time = time.time()
    field_results = engine.search(test_query, field_filter=["owner"])
    field_time = (time.time() - start_time) * 1000
    
    print(f"   📊 Basic search: {len(basic_results)} results in {basic_time:.2f}ms")
    print(f"   📊 County filtered: {len(county_results)} results in {county_time:.2f}ms")
    print(f"   📊 Field filtered: {len(field_results)} results in {field_time:.2f}ms")
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED!")
    print("="*80)

if __name__ == "__main__":
    test_search_features()
