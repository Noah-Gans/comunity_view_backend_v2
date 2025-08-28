#!/usr/bin/env python3
"""
Debug word extraction from owner names
"""

from search_engine import SearchEngine

def debug_word_extraction():
    """Debug why word extraction is missing some ladd entries"""
    
    engine = SearchEngine()
    print("✅ Search engine loaded")
    
    # The 3 Teton County WY entries we're looking for
    target_entries = [
        "LADD, BRIAN ANDREW",
        "LADD, EDWARD L. REVOCABLE TRUST & LHL TRUST", 
        "CARLMAN, LEONARD R. & ANN LADD"
    ]
    
    print("\n🔍 Debugging word extraction for target entries:")
    
    for target_owner in target_entries:
        print(f"\n📝 Owner: {target_owner}")
        
        # Find this entry in the data
        entry = None
        for e in engine.search_data:
            if e.get('owner') == target_owner:
                entry = e
                break
        
        if entry:
            print(f"   ✅ Found in data")
            print(f"   UID: {entry.get('global_parcel_uid', 'N/A')}")
            print(f"   County: {entry.get('county', 'N/A')}, {entry.get('state', 'N/A')}")
            
            # Check if it's in the word index
            owner_lower = target_owner.lower()
            words = owner_lower.split()
            print(f"   Words extracted: {words}")
            
            # Check each word in the word index
            for word in words:
                if len(word) > 2:  # Only words longer than 2 chars are indexed
                    if word in engine.word_index:
                        indices = engine.word_index[word]
                        print(f"   ✅ Word '{word}' in index: {len(indices)} entries")
                        
                        # Check if this entry is in the word index
                        entry_idx = None
                        for i, e in enumerate(engine.search_data):
                            if e.get('owner') == target_owner:
                                entry_idx = i
                                break
                        
                        if entry_idx is not None and entry_idx in indices:
                            print(f"      ✅ Entry found in word index for '{word}'")
                        else:
                            print(f"      ❌ Entry NOT found in word index for '{word}'")
                    else:
                        print(f"   ❌ Word '{word}' NOT in word index")
                else:
                    print(f"   ⏭️  Word '{word}' too short (≤2 chars), not indexed")
        else:
            print(f"   ❌ NOT FOUND in data")
    
    # Check the word index building logic
    print(f"\n🔍 Word index building analysis:")
    print(f"   Total entries in data: {len(engine.search_data)}")
    print(f"   Total words in word index: {len(engine.word_index)}")
    
    # Count how many entries have "ladd" in owner
    ladd_in_owner = 0
    for entry in engine.search_data:
        owner = entry.get('owner', '')
        if 'ladd' in owner.lower():
            ladd_in_owner += 1
    
    print(f"   Entries with 'ladd' in owner: {ladd_in_owner}")
    print(f"   Entries in word index for 'ladd': {len(engine.word_index.get('ladd', []))}")
    
    if ladd_in_owner != len(engine.word_index.get('ladd', [])):
        print(f"   ⚠️  MISMATCH: {ladd_in_owner} entries have 'ladd' but only {len(engine.word_index.get('ladd', []))} are indexed!")

if __name__ == "__main__":
    debug_word_extraction()
