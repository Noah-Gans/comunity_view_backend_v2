#!/usr/bin/env python3
"""
Debug the word index for "ladd" specifically
"""

from search_engine import SearchEngine

def debug_word_index():
    """Debug the word index for ladd"""
    
    engine = SearchEngine()
    print("✅ Search engine loaded")
    
    # Check the word index for "ladd"
    word = "ladd"
    print(f"\n🔍 Word index for '{word}':")
    
    if word in engine.word_index:
        indices = engine.word_index[word]
        print(f"   Found {len(indices)} entries in word index")
        
        # Check for duplicates
        unique_indices = set(indices)
        print(f"   Unique indices: {len(unique_indices)}")
        
        if len(indices) != len(unique_indices):
            print("   ⚠️  DUPLICATES FOUND!")
        
        # Show all entries
        print(f"\n   📋 All entries:")
        for i, idx in enumerate(indices):
            entry = engine.search_data[idx]
            owner = entry.get("owner", "N/A")
            uid = entry.get("global_parcel_uid", "N/A")
            print(f"     {i+1}. {owner} ({uid})")
        
        # Check if all 4 expected entries are there
        expected_owners = [
            "TAYLOR, JUSTIN LADD",
            "LADD, BRIAN ANDREW", 
            "LADD, EDWARD L. REVOCABLE TRUST & LHL TRUST",
            "CARLMAN, LEONARD R. & ANN LADD"
        ]
        
        print(f"\n   🎯 Checking for expected owners:")
        found_owners = []
        for idx in indices:
            entry = engine.search_data[idx]
            owner = entry.get("owner", "")
            if owner in expected_owners:
                found_owners.append(owner)
                print(f"     ✅ Found: {owner}")
            else:
                print(f"     ❌ Unexpected: {owner}")
        
        print(f"\n   📊 Summary: Found {len(found_owners)} out of {len(expected_owners)} expected owners")
        
    else:
        print(f"   ❌ Word '{word}' not found in word index")
    
    # Check what words ARE in the index
    print(f"\n🔍 Sample words in word index:")
    sample_words = list(engine.word_index.keys())[:10]
    for word in sample_words:
        count = len(engine.word_index[word])
        print(f"   '{word}': {count} entries")

if __name__ == "__main__":
    debug_word_index()
