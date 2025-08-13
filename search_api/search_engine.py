import json
import re
import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class SearchEngine:
    """
    Optimized search engine with pre-computed indexes and faster search algorithms
    """
    
    def __init__(self, search_index_path: str = None):
        if search_index_path is None:
            from pathlib import Path
            search_api_dir = Path(__file__).parent
            search_index_path = search_api_dir / "search_index.json"
        
        self.search_index_path = str(search_index_path)
        self.search_data = None
        self.owner_index = defaultdict(list)  # owner -> list of entry indices
        self.parcel_index = defaultdict(list)  # parcel_id -> list of entry indices
        self.address_index = defaultdict(list)  # address -> list of entry indices
        self.word_index = defaultdict(list)     # word -> list of entry indices
        
        self._load_search_data()
        self._build_indexes()
    
    def _load_search_data(self):
        """Load the search index data"""
        try:
            with open(self.search_index_path, 'r') as f:
                self.search_data = json.load(f)
            logger.info(f"✅ Loaded search index with {len(self.search_data)} entries")
        except FileNotFoundError:
            logger.error(f"❌ Search index file not found: {self.search_index_path}")
            self.search_data = []
        except Exception as e:
            logger.error(f"❌ Error loading search index: {e}")
            self.search_data = []
    
    def _build_indexes(self):
        """Build inverted indexes for faster searching"""
        if not self.search_data:
            return
        
        logger.info("🔨 Building search indexes...")
        
        for idx, entry in enumerate(self.search_data):
            # Index by owner name
            owner = entry.get("owner", "").lower().strip()
            if owner:
                self.owner_index[owner].append(idx)
                # Also index by words in owner name
                for word in owner.split():
                    if len(word) > 2:  # Only index words longer than 2 chars
                        self.word_index[word].append(idx)
            
            # Index by parcel ID
            parcel_id = entry.get("pidn", "").lower().strip()
            if parcel_id:
                self.parcel_index[parcel_id].append(idx)
                # Also index by partial parcel IDs (common search pattern)
                for i in range(3, len(parcel_id) + 1):
                    partial = parcel_id[:i]
                    self.parcel_index[partial].append(idx)
            
            # Index by address
            address = entry.get("mailing_address", "")
            if address:
                address_lower = address.lower().strip()
                self.address_index[address_lower].append(idx)
                # Index by words in address
                for word in address_lower.split():
                    if len(word) > 2:
                        self.word_index[word].append(idx)
        
        logger.info(f"✅ Built indexes: {len(self.owner_index)} owners, {len(self.parcel_index)} parcels, {len(self.word_index)} words")
    
    def _fast_search(self, query: str) -> List[int]:
        """Fast search using pre-built indexes"""
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        # Get candidate indices from indexes
        candidates = set()
        
        # Check exact matches first (fastest)
        if query_lower in self.owner_index:
            candidates.update(self.owner_index[query_lower])
        if query_lower in self.parcel_index:
            candidates.update(self.parcel_index[query_lower])
        if query_lower in self.address_index:
            candidates.update(self.address_index[query_lower])
        
        # Check word matches
        for word in query_words:
            if len(word) > 2 and word in self.word_index:
                candidates.update(self.word_index[word])
        
        # If we have enough exact matches, return early
        if len(candidates) >= 200:
            return list(candidates)[:200]
        
        # Add partial matches for parcel IDs (common search pattern)
        if len(query_lower) >= 3:
            for partial in range(3, len(query_lower) + 1):
                partial_query = query_lower[:partial]
                if partial_query in self.parcel_index:
                    candidates.update(self.parcel_index[partial_query])
        
        return list(candidates)
    
    def _score_and_filter(self, query: str, candidate_indices: List[int]) -> List[Dict[str, Any]]:
        """Score and filter candidates to get final results"""
        if not candidate_indices:
            return []
        
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        scored_results = []
        
        for idx in candidate_indices:
            entry = self.search_data[idx]
            score = 0
            
            # Owner name scoring (highest priority)
            owner = entry.get("owner", "").lower()
            if owner:
                if query_lower in owner:
                    score += 1000  # Exact substring match
                elif all(word in owner for word in query_words):
                    score += 800   # All words present
                elif any(word in owner for word in query_words):
                    score += 400   # Some words present
            
            # Parcel ID scoring
            parcel_id = entry.get("pidn", "").lower()
            if parcel_id:
                if query_lower in parcel_id:
                    score += 600   # Exact substring match
                elif parcel_id.startswith(query_lower):
                    score += 500   # Starts with query
            
            # Address scoring
            address = entry.get("mailing_address", "")
            if address:
                address_lower = address.lower()
                if query_lower in address_lower:
                    score += 300   # Exact substring match
                elif any(word in address_lower for word in query_words):
                    score += 150   # Some words present
            
            # Boost for complete matches
            if score > 0:
                if entry.get("physical_address"):
                    score += 50
                if entry.get("clerk_rec"):
                    score += 25
                
                scored_results.append({
                    "entry": entry,
                    "score": score
                })
        
        # Sort by score and return top results
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return [result["entry"] for result in scored_results[:200]]
    
    def search(self, query: str, county_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Optimized search with pre-built indexes"""
        if not self.search_data:
            logger.warning("⚠️  No search data loaded")
            return []
        
        if not query or not query.strip():
            logger.warning("⚠️  Empty query")
            return []
        
        # Apply county filter if provided
        if county_filter:
            # Filter the search data by county first
            filtered_data = [entry for entry in self.search_data if entry.get("county") in county_filter]
            if not filtered_data:
                return []
            # Rebuild indexes for filtered data (simplified approach)
            return self._search_filtered(query, filtered_data)
        
        # Fast search using indexes
        candidate_indices = self._fast_search(query)
        
        if not candidate_indices:
            return []
        
        # Score and filter candidates
        results = self._score_and_filter(query, candidate_indices)
        
        logger.info(f"🔍 Query '{query}' found {len(results)} results from {len(candidate_indices)} candidates")
        return results
    
    def _search_filtered(self, query: str, filtered_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Search within filtered data (fallback for county filtering)"""
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        scored_results = []
        
        for entry in filtered_data:
            score = 0
            
            # Simple scoring for filtered search
            owner = entry.get("owner", "").lower()
            if owner and any(word in owner for word in query_words):
                score += 500
            
            parcel_id = entry.get("pidn", "").lower()
            if parcel_id and query_lower in parcel_id:
                score += 400
            
            if score > 0:
                scored_results.append({
                    "entry": entry,
                    "score": score
                })
        
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return [result["entry"] for result in scored_results[:200]]
    
    def reload_search_data(self):
        """Reload the search index data and rebuild indexes"""
        self._load_search_data()
        self._build_indexes()
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get statistics about the search index"""
        if not self.search_data:
            return {"total_entries": 0, "counties": []}
        
        counties = {}
        for entry in self.search_data:
            county = entry.get("county", "unknown")
            counties[county] = counties.get(county, 0) + 1
        
        return {
            "total_entries": len(self.search_data),
            "counties": counties,
            "index_sizes": {
                "owner_index": len(self.owner_index),
                "parcel_index": len(self.parcel_index),
                "word_index": len(self.word_index)
            }
        }
