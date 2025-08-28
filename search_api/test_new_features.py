#!/usr/bin/env python3
"""
Test new search features: county codes, field filtering, spatial search
"""

from search_engine import SearchEngine

def test_new_features():
    """Test all the new search features"""
    
    # Initialize search engine
    engine = SearchEngine()
    print("✅ Search engine loaded")
    
    # Test 1: County filtering with county codes
    print("\n🔍 Test 1: County filtering with county codes")
    wy_results = engine.search('ladd', county_filter=['teton_county_wy'])
    id_results = engine.search('ladd', county_filter=['teton_county_id'])
    print(f"📊 WY results: {len(wy_results)}")
    print(f"📊 ID results: {len(id_results)}")
    
    # Test 2: Field-specific search
    print("\n🔍 Test 2: Field-specific search")
    owner_results = engine.search('ladd', field_filter=['owner'])
    pidn_results = engine.search('ladd', field_filter=['pidn'])
    print(f"📊 Owner field results: {len(owner_results)}")
    print(f"📊 PIDN field results: {len(pidn_results)}")
    
    # Test 3: Spatial search
    print("\n🔍 Test 3: Spatial search")
    spatial_results = engine.search('ladd', spatial_params={'lat': 43.5, 'lon': -110.2})
    print(f"📊 Spatial search results: {len(spatial_results)}")
    
    # Test 4: Combined filters
    print("\n🔍 Test 4: Combined filters")
    combined_results = engine.search(
        'ladd', 
        county_filter=['teton_county_wy'],
        field_filter=['owner'],
        spatial_params={'lat': 43.5, 'lon': -110.2}
    )
    print(f"📊 Combined filter results: {len(combined_results)}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    test_new_features()
