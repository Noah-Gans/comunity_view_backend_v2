#!/usr/bin/env python3
"""
Quick test to verify "ladd" search returns 4 results
"""

from search_engine import SearchEngine

def test_ladd_search():
    """Test that ladd search returns 4 results"""
    
    engine = SearchEngine()
    print("✅ Search engine loaded")
    print(f"📊 Total entries in index: {len(engine.search_data)}")
    
    # Test basic search for "ladd"
    print("\n🔍 Testing 'ladd' search...")
    results = engine.search("ladd")
    print(f"📊 Results: {len(results)}")
    
    if results:
        print("\n🎯 All results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. Owner: {result.get('owner', 'N/A')}")
            print(f"      PIDN: {result.get('pidn', 'N/A')}")
            print(f"      County: {result.get('county', 'N/A')}, {result.get('state', 'N/A')}")
            print(f"      UID: {result.get('global_parcel_uid', 'N/A')}")
            print()
    
    # Expected: 4 results
    expected = 4
    if len(results) == expected:
        print(f"✅ SUCCESS: Found {len(results)} results (expected {expected})")
    else:
        print(f"❌ FAILED: Found {len(results)} results (expected {expected})")

if __name__ == "__main__":
    test_ladd_search()
