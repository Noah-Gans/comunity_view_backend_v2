#!/usr/bin/env python3
"""
Test independent field search functionality
"""

from search_engine import SearchEngine

def test_field_search():
    """Test that fields can be searched independently"""
    
    # Initialize search engine
    engine = SearchEngine()
    print("✅ Search engine loaded")
    
    # Test 1: Search ONLY in owner field
    print("\n🔍 Test 1: Search ONLY in owner field")
    owner_only_results = engine.search('ladd', field_filter=['owner'])
    print(f"📊 Owner-only results: {len(owner_only_results)}")
    
    # Test 2: Search ONLY in pidn field
    print("\n🔍 Test 2: Search ONLY in pidn field")
    pidn_only_results = engine.search('ladd', field_filter=['pidn'])
    print(f"📊 PIDN-only results: {len(pidn_only_results)}")
    
    # Test 3: Search in BOTH fields (should return results from either)
    print("\n🔍 Test 3: Search in BOTH fields (independent)")
    both_fields_results = engine.search('ladd', field_filter=['owner', 'pidn'])
    print(f"📊 Both fields results: {len(both_fields_results)}")
    
    # Test 4: Search in all searchable fields
    print("\n🔍 Test 4: Search in all fields")
    all_fields_results = engine.search('ladd', field_filter=['owner', 'pidn', 'mailing_address', 'physical_address', 'county'])
    print(f"📊 All fields results: {len(all_fields_results)}")
    
    # Test 5: Compare with no field filter (should be same as all fields)
    print("\n🔍 Test 5: No field filter (default)")
    no_filter_results = engine.search('ladd')
    print(f"📊 No filter results: {len(no_filter_results)}")
    
    print("\n✅ All tests completed!")
    
    # Show some sample results
    if owner_only_results:
        print(f"\n📋 Sample owner-only result: {owner_only_results[0].get('owner', 'N/A')}")
    if pidn_only_results:
        print(f"📋 Sample PIDN-only result: {pidn_only_results[0].get('pidn', 'N/A')}")

if __name__ == "__main__":
    test_field_search()
