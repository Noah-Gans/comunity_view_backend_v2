#!/usr/bin/env python3
"""
Debug script to understand why "ladd" search returns only 2 results
"""

from search_engine import SearchEngine

def debug_ladd_search():
    """Debug the ladd search issue"""
    
    engine = SearchEngine()
    print("✅ Search engine loaded")
    print(f"📊 Total entries in index: {len(engine.search_data)}")
    
    # Check what's in the indexes for "ladd"
    query = "ladd"
    query_lower = query.lower()
    
    print(f"\n🔍 Debugging search for: '{query}'")
    
    # Check owner index
    print(f"\n📋 Owner index entries for '{query_lower}':")
    if query_lower in engine.owner_index:
        owner_indices = engine.owner_index[query_lower]
        print(f"   Direct match: {len(owner_indices)} entries")
        for idx in owner_indices[:3]:  # Show first 3
            entry = engine.search_data[idx]
            print(f"     - {entry.get('owner', 'N/A')} ({entry.get('global_parcel_uid', 'N/A')})")
    
    # Check word index
    print(f"\n📋 Word index entries for '{query_lower}':")
    if query_lower in engine.word_index:
        word_indices = engine.word_index[query_lower]
        print(f"   Word match: {len(word_indices)} entries")
        for idx in word_indices[:3]:  # Show first 3
            entry = engine.search_data[idx]
            print(f"     - {entry.get('owner', 'N/A')} ({entry.get('global_parcel_uid', 'N/A')})")
    
    # Check partial matches
    print(f"\n📋 Partial matches in owner names:")
    partial_matches = []
    for entry in engine.search_data:
        owner = entry.get("owner", "")
        if owner and query_lower in owner.lower():
            partial_matches.append(entry)
    
    print(f"   Found {len(partial_matches)} entries with '{query_lower}' in owner")
    for entry in partial_matches:
        print(f"     - {entry.get('owner', 'N/A')} ({entry.get('global_parcel_uid', 'N/A')})")
    
    # Check what the fast search returns
    print(f"\n📋 Fast search candidates:")
    candidates = engine._fast_search(query)
    print(f"   Fast search returned {len(candidates)} candidates")
    
    # Check what scoring returns
    print(f"\n📋 Scoring results:")
    scored_results = engine._score_and_filter(query, candidates)
    print(f"   Scoring returned {len(scored_results)} results")
    
    # Manual search through all data
    print(f"\n📋 Manual search through all data:")
    manual_matches = []
    for entry in engine.search_data:
        owner = entry.get("owner", "")
        if owner and query_lower in owner.lower():
            manual_matches.append(entry)
    
    print(f"   Manual search found {len(manual_matches)} matches")
    for entry in manual_matches:
        print(f"     - {entry.get('owner', 'N/A')} ({entry.get('global_parcel_uid', 'N/A')})")

if __name__ == "__main__":
    debug_ladd_search()
