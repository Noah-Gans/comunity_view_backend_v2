#!/usr/bin/env python3
"""
Debug script to check county and state values in search index
"""

import json

def debug_counties():
    """Check county and state values in search index"""
    
    # Load search index
    with open('search_index.json', 'r') as f:
        data = json.load(f)
    
    print(f"✅ Loaded search index with {len(data)} entries")
    
    # Check unique county/state combinations
    county_state_combos = {}
    for entry in data:
        county = entry.get('county', 'None')
        state = entry.get('state', 'None')
        uid = entry.get('global_parcel_uid', 'None')
        
        combo = f"{county}, {state}"
        if combo not in county_state_combos:
            county_state_combos[combo] = []
        county_state_combos[combo].append(uid)
    
    print("\n🔍 County/State combinations found:")
    for combo, uids in county_state_combos.items():
        print(f"  \"{combo}\": {len(uids)} entries")
        print(f"    Sample UIDs: {uids[:3]}")
    
    # Check what happens when filtering
    print("\n🔍 Testing county filtering:")
    test_filter = ["Teton County, WY"]
    print(f"  Filter: {test_filter}")
    
    filtered = [entry for entry in data if entry.get('county') + ', ' + entry.get('state') in test_filter]
    print(f"  Results: {len(filtered)} entries")
    
    if filtered:
        sample = filtered[0]
        print(f"  Sample result: county=\"{sample.get('county')}\", state=\"{sample.get('state')}\"")

if __name__ == "__main__":
    debug_counties()
