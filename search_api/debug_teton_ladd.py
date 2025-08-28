#!/usr/bin/env python3
"""
Debug script to find missing Teton County WY LADD entries
"""

from search_engine import SearchEngine

def debug_teton_ladd():
    """Debug missing Teton County WY LADD entries"""
    
    engine = SearchEngine()
    print("✅ Search engine loaded")
    print(f"📊 Total entries in index: {len(engine.search_data)}")
    
    # Expected Teton County WY LADD entries
    expected_entries = [
        {
            "owner": "LADD, BRIAN ANDREW",
            "pidn": "22-41-16-34-2-77-007",
            "county": "Teton County",
            "state": "WY"
        },
        {
            "owner": "LADD, EDWARD L. REVOCABLE TRUST & LHL TRUST", 
            "pidn": "22-41-17-33-3-03-047",
            "county": "Teton County",
            "state": "WY"
        },
        {
            "owner": "CARLMAN, LEONARD R. & ANN LADD",
            "pidn": "22-41-17-22-1-01-020", 
            "county": "Teton County",
            "state": "WY"
        }
    ]
    
    print("\n🔍 Looking for expected Teton County WY LADD entries:")
    
    # Search for each expected entry
    for i, expected in enumerate(expected_entries, 1):
        print(f"\n📝 Expected Entry {i}:")
        print(f"   Owner: {expected['owner']}")
        print(f"   PIDN: {expected['pidn']}")
        print(f"   County: {expected['county']}, {expected['state']}")
        
        # Search by owner name
        owner_results = engine.search(expected['owner'])
        print(f"   🔍 Search by owner: {len(owner_results)} results")
        
        # Search by PIDN
        pidn_results = engine.search(expected['pidn'])
        print(f"   🔍 Search by PIDN: {len(pidn_results)} results")
        
        # Manual search through all data
        manual_matches = []
        for entry in engine.search_data:
            if (entry.get('owner', '') == expected['owner'] and 
                entry.get('pidn', '') == expected['pidn']):
                manual_matches.append(entry)
        
        print(f"   🔍 Manual search: {len(manual_matches)} exact matches")
        
        if manual_matches:
            entry = manual_matches[0]
            print(f"   ✅ Found: {entry.get('global_parcel_uid', 'N/A')}")
            print(f"      County: {entry.get('county', 'N/A')}, {entry.get('state', 'N/A')}")
        else:
            print(f"   ❌ NOT FOUND in search data!")
    
    # Check word index for "ladd"
    print(f"\n🔍 Word index for 'ladd':")
    if 'ladd' in engine.word_index:
        indices = engine.word_index['ladd']
        print(f"   Found {len(indices)} entries in word index")
        
        # Show all entries with "ladd" in owner
        teton_wy_ladd = []
        for idx in indices:
            entry = engine.search_data[idx]
            owner = entry.get('owner', '')
            county = entry.get('county', '')
            state = entry.get('state', '')
            
            if 'ladd' in owner.lower() and county == 'Teton County' and state == 'WY':
                teton_wy_ladd.append(entry)
        
        print(f"   📊 Teton County WY entries with 'ladd': {len(teton_wy_ladd)}")
        for entry in teton_wy_ladd:
            print(f"      - {entry.get('owner', 'N/A')} ({entry.get('pidn', 'N/A')})")
    
    # Check if these entries exist in the raw data
    print(f"\n🔍 Checking raw data for Teton County WY entries:")
    teton_wy_entries = []
    for entry in engine.search_data:
        county = entry.get('county', '')
        state = entry.get('state', '')
        if county == 'Teton County' and state == 'WY':
            teton_wy_entries.append(entry)
    
    print(f"   📊 Total Teton County WY entries: {len(teton_wy_entries)}")
    
    # Look for any entries with "ladd" in Teton County WY
    teton_wy_with_ladd = []
    for entry in teton_wy_entries:
        owner = entry.get('owner', '')
        if 'ladd' in owner.lower():
            teton_wy_with_ladd.append(entry)
    
    print(f"   📊 Teton County WY entries with 'ladd': {len(teton_wy_with_ladd)}")
    for entry in teton_wy_with_ladd:
        print(f"      - {entry.get('owner', 'N/A')} ({entry.get('pidn', 'N/A')})")

if __name__ == "__main__":
    debug_teton_ladd()
