#!/usr/bin/env python3
"""
Performance test script for the search algorithm
"""

import time
import json
import random
from pathlib import Path
from search_engine import SearchEngine

def generate_test_queries(search_data, num_queries=10):
    """Generate realistic test queries from the data"""
    queries = []
    
    # Get some sample owner names
    owners = [entry.get("owner", "") for entry in search_data[:1000] if entry.get("owner")]
    owners = [owner for owner in owners if len(owner.strip()) > 3]
    
    # Get some sample parcel IDs
    parcel_ids = [entry.get("pidn", "") for entry in search_data[:1000] if entry.get("pidn")]
    parcel_ids = [pid for pid in parcel_ids if len(pid.strip()) > 3]
    
    # Generate different types of queries
    for i in range(num_queries):
        if i % 3 == 0 and owners:
            # Owner name queries
            owner = random.choice(owners)
            words = owner.split()[:2]  # Take first 2 words
            queries.append(" ".join(words))
        elif i % 3 == 1 and parcel_ids:
            # Parcel ID queries
            pid = random.choice(parcel_ids)
            queries.append(pid[:6])  # First 6 characters
        else:
            # Random text queries
            if owners:
                owner = random.choice(owners)
                queries.append(owner[:4])
    
    return queries

def benchmark_search(search_engine, queries, iterations=3):
    """Benchmark search performance"""
    print(f"🔍 Benchmarking {len(queries)} queries with {iterations} iterations each...")
    print("=" * 60)
    
    total_time = 0
    total_results = 0
    
    for i, query in enumerate(queries):
        query_times = []
        query_results = []
        
        for j in range(iterations):
            start_time = time.time()
            results = search_engine.search(query)
            end_time = time.time()
            
            query_times.append(end_time - start_time)
            query_results.append(len(results))
        
        avg_time = sum(query_times) / len(query_times)
        avg_results = sum(query_results) / len(query_results)
        
        total_time += avg_time
        total_results += avg_results
        
        print(f"Query {i+1:2d}: '{query:20s}' | Time: {avg_time*1000:6.2f}ms | Results: {int(avg_results):3d}")
    
    print("=" * 60)
    print(f"📊 Average query time: {(total_time/len(queries))*1000:.2f}ms")
    print(f"📊 Total results found: {total_results}")
    print(f"📊 Queries per second: {len(queries)/total_time:.1f}")
    
    return total_time / len(queries)

def profile_search_algorithm(search_engine, sample_query):
    """Profile the search algorithm to identify bottlenecks"""
    print(f"\n🔍 Profiling search algorithm with query: '{sample_query}'")
    print("=" * 60)
    
    # Load data to see structure
    search_data = search_engine.search_data
    if not search_data:
        print("❌ No search data available")
        return
    
    print(f"📊 Total entries: {len(search_data)}")
    print(f"🔍 Sample entry keys: {list(search_data[0].keys())}")
    
    # Test with different query lengths
    test_queries = [
        sample_query[:3],    # Short query
        sample_query[:6],    # Medium query  
        sample_query,        # Full query
        sample_query + " extra words for longer query"  # Long query
    ]
    
    for query in test_queries:
        start_time = time.time()
        results = search_engine.search(query)
        end_time = time.time()
        
        print(f"Query '{query:30s}' | Time: {(end_time-start_time)*1000:6.2f}ms | Results: {len(results)}")

def main():
    """Main performance test function"""
    print("🚀 Starting Search Algorithm Performance Test")
    print("=" * 60)
    
    # Initialize search engine
    search_engine = SearchEngine()
    
    if not search_engine.search_data:
        print("❌ No search data available. Run search_file_generator.py first.")
        return
    
    print(f"✅ Loaded search index with {len(search_engine.search_data)} entries")
    
    # Generate test queries
    test_queries = generate_test_queries(search_engine.search_data, num_queries=15)
    
    # Benchmark performance
    avg_time = benchmark_search(search_engine, test_queries)
    
    # Profile algorithm
    if test_queries:
        profile_search_algorithm(search_engine, test_queries[0])
    
    print(f"\n🎯 Performance Summary:")
    print(f"   Average query time: {avg_time*1000:.2f}ms")
    print(f"   Queries per second: {1/avg_time:.1f}")
    
    if avg_time > 0.1:  # More than 100ms
        print(f"   ⚠️  Performance could be improved (target: <100ms)")
    else:
        print(f"   ✅ Performance is good!")

if __name__ == "__main__":
    main()
