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
        """Load the search index data and pre-clean it"""
        try:
            with open(self.search_index_path, 'r') as f:
                self.search_data = json.load(f)
            logger.info(f"✅ Loaded search index with {len(self.search_data)} entries")
            self.search_data = self._pre_clean_data(self.search_data)
            
            
        except FileNotFoundError:
            logger.error(f"❌ Search index file not found: {self.search_index_path}")
            self.search_data = []
        except Exception as e:
            logger.error(f"❌ Error loading search index: {e}")
            self.search_data = []
    
    def _build_indexes(self):
        """Build search indexes from the data"""
        logger.info("🔨 Building search indexes...")
        
        # Clear existing indexes
        self.owner_index = defaultdict(list)
        self.parcel_index = defaultdict(list)
        self.address_index = defaultdict(list)
        self.word_index = defaultdict(list)
        
        for idx, entry in enumerate(self.search_data):
            # Use original values for indexing, but clean them for search
            owner = entry.get('owner', '')
            pidn = entry.get('pidn', '')
            mailing = entry.get('mailing_address', '')
            physical = entry.get('physical_address', '')
            county = entry.get('county', '')
            
            # Clean text for indexing (but don't modify original data)
            owner_clean = self._clean_text_for_search(owner)
            pidn_clean = self._clean_text_for_search(pidn)
            mailing_clean = self._clean_text_for_search(mailing)
            physical_clean = self._clean_text_for_search(physical)
            county_clean = self._clean_text_for_search(county)
            
            # Index by cleaned owner name
            if owner_clean:
                self.owner_index[owner_clean].append(idx)
                
                # Also index by words in owner name (using cleaned text)
                for word in owner_clean.split():
                    if len(word) > 2:  # Only index words longer than 2 chars
                        self.word_index[word].append(idx)
            
            # Index by cleaned PIDN
            if pidn_clean:
                self.parcel_index[pidn_clean].append(idx)
                
                # Also index by partial parcel IDs (common search pattern)
                for i in range(3, len(pidn_clean) + 1):
                    partial = pidn_clean[:i]
                    self.parcel_index[partial].append(idx)
            
            # Index by cleaned addresses
            if mailing_clean:
                self.address_index[mailing_clean].append(idx)
                # Index by words in address (using cleaned text)
                for word in mailing_clean.split():
                    if len(word) > 2:
                        self.word_index[word].append(idx)
            
            if physical_clean:
                self.address_index[physical_clean].append(idx)
                # Index by words in address (using cleaned text)
                for word in physical_clean.split():
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
    
    def _score_and_filter(self, query: str, candidate_indices: List[int], field_filter: Optional[List[str]] = None, spatial_params: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Score and filter candidates to get final results"""
        if not candidate_indices:
            return []
        
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        scored_results = []
        
        for idx in candidate_indices:
            entry = self.search_data[idx]
            
            # Use field-specific or all-field scoring
            if field_filter:
                score = self._score_by_fields(entry, query_lower, query_words, field_filter)
            else:
                score = self._score_all_fields(entry, query_lower, query_words)
            
            # Apply spatial boost if coordinates provided
            if spatial_params and score > 0:
                spatial_boost = self._calculate_spatial_boost(entry, spatial_params)
                score += spatial_boost
            
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
    
    def search(self, query: str, county_filter: Optional[List[str]] = None, field_filter: Optional[List[str]] = None, spatial_params: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Optimized search with pre-built indexes and advanced filtering + LINEAR FALLBACK"""
        if not self.search_data:
            logger.warning("⚠️  No search data loaded")
            return []
        
        if not query or not query.strip():
            logger.warning("⚠️  Empty query")
            return []
        
        # Apply county filter if provided (now expects county codes like teton_county_wy)
        if county_filter:
            filtered_data = []
            for entry in self.search_data:
                # Extract county code from global_parcel_uid (e.g., "teton_county_wy_000001" -> "teton_county_wy")
                uid = entry.get("global_parcel_uid", "")
                if uid and "_" in uid:
                    county_code = uid.split("_")[0] + "_" + uid.split("_")[1] + "_" + uid.split("_")[2]
                    if county_code in county_filter:
                        filtered_data.append(entry)
            
            if not filtered_data:
                return []
            # Search within filtered data
            return self._search_filtered(query, filtered_data, field_filter, spatial_params)
        
        # Fast search using indexes
        candidate_indices = self._fast_search(query)
        
        # If fast search returns no candidates, return empty
        if not candidate_indices:
            return []
        
        # Score and filter candidates
        results = self._score_and_filter(query, candidate_indices, field_filter, spatial_params)
        
        logger.info(f"🔍 Query '{query}' found {len(results)} results from {len(candidate_indices)} candidates")
        return results
    
    def _search_filtered(self, query: str, filtered_data: List[Dict[str, Any]], field_filter: Optional[List[str]] = None, spatial_params: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Search within filtered data with advanced filtering"""
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        scored_results = []
        
        for entry in filtered_data:
            score = 0
            
            # Field-specific search if specified
            if field_filter:
                score = self._score_by_fields(entry, query_lower, query_words, field_filter)
            else:
                # Default scoring for all fields
                score = self._score_all_fields(entry, query_lower, query_words)
            
            # Apply spatial boost if coordinates provided
            if spatial_params and score > 0:
                spatial_boost = self._calculate_spatial_boost(entry, spatial_params)
                score += spatial_boost
            
            if score > 0:
                scored_results.append({
                    "entry": entry,
                    "score": score
                })
        
        # Sort by score (spatial results will be prioritized)
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return [result["entry"] for result in scored_results[:200]]
    
    def _score_by_fields(self, entry: Dict[str, Any], query_lower: str, query_words: List[str], field_filter: List[str]) -> int:
        """Score entry based on specific fields only - ANY field can match"""
        score = 0
        
        # Check if ANY of the specified fields match (not all)
        for field in field_filter:
            field_lower = field.lower()
            field_score = 0
            
            if field_lower == "owner":
                owner = entry.get("owner", "")
                if owner and any(word in owner.lower() for word in query_words):
                    field_score = 500
            elif field_lower == "pidn":
                parcel_id = entry.get("pidn", "")
                if parcel_id and query_lower in parcel_id.lower():
                    field_score = 400
            elif field_lower == "mailing_address":
                address = entry.get("mailing_address", "")
                if address and any(word in address.lower() for word in query_words):
                    field_score = 300
            elif field_lower == "physical_address":
                address = entry.get("physical_address", "")
                if address and any(word in address.lower() for word in query_words):
                    field_score = 300
            elif field_lower == "county":
                county = entry.get("county", "")
                if county and query_lower in county.lower():
                    field_score = 200
            
            # Use the highest score from any matching field
            score = max(score, field_score)
        
        return score
    
    def _score_all_fields(self, entry: Dict[str, Any], query_lower: str, query_words: List[str]) -> int:
        """Score entry across all searchable fields - RESTORED ORIGINAL LOGIC"""
        score = 0
        
        # Owner name scoring (highest priority)
        owner = entry.get("owner", "")
        if owner:
            if query_lower in owner.lower():
                score += 1000  # Exact substring match
            elif all(word in owner.lower() for word in query_words):
                score += 800   # All words present
            elif any(word in owner.lower() for word in query_words):
                score += 400   # Some words present
        
        # Parcel ID scoring
        parcel_id = entry.get("pidn", "")
        if parcel_id:
            if query_lower in parcel_id.lower():
                score += 600   # Exact substring match
            elif parcel_id.lower().startswith(query_lower):
                score += 500   # Starts with query
        
        # Address scoring
        address = entry.get("mailing_address", "")
        if address:
            address_lower = address.lower()
            if query_lower in address_lower:
                score += 300   # Exact substring match
            elif any(word in address_lower for word in query_words):
                score += 150   # Some words present
        
        physical_address = entry.get("physical_address", "")
        if physical_address:
            physical_lower = physical_address.lower()
            if query_lower in physical_lower:
                score += 300   # Exact substring match
            elif any(word in physical_lower for word in query_words):
                score += 150   # Some words present
        
        return score
    
    def _calculate_spatial_boost(self, entry: Dict[str, Any], spatial_params: Dict[str, float]) -> int:
        """Calculate spatial boost based on proximity to lat/lon"""
        bbox = entry.get("bbox")
        if not bbox or len(bbox) != 4:
            return 0
        
        # Calculate center of bbox
        center_lon = (bbox[0] + bbox[2]) / 2
        center_lat = (bbox[1] + bbox[3]) / 2
        
        # Calculate distance (simple Euclidean for speed)
        target_lon = spatial_params["lon"]
        target_lat = spatial_params["lat"]
        
        # Rough distance calculation (degrees)
        distance = ((center_lon - target_lon) ** 2 + (center_lat - target_lat) ** 2) ** 0.5
        
        # Convert to spatial boost (closer = higher boost)
        # Max boost of 1000 for very close, decreasing with distance
        if distance < 0.01:  # Very close (< ~1km)
            return 1000
        elif distance < 0.1:  # Close (< ~10km)
            return 500
        elif distance < 0.5:  # Moderate (< ~50km)
            return 100
        else:
            return 0
    
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
    
    def _pre_clean_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Pre-clean all searchable text fields to remove punctuation and normalize text"""
        import re
        
        logger.info("🧹 Pre-cleaning searchable text fields...")
        
        # Fields to clean
        text_fields = ['owner', 'pidn', 'mailing_address', 'physical_address', 'county']
        
        for entry in data:
            for field in text_fields:
                if field in entry and entry[field]:
                    # Store original value
                    original = entry[field]
                    
                    # Create cleaned version for searching
                    cleaned = self._clean_text_for_search(original)
                    
                    # Store both versions
                    entry[f"{field}_original"] = original  # Keep original for display
                    entry[field] = cleaned  # Use cleaned for indexing/searching
        
        logger.info("✅ Data pre-cleaning completed")
        return data
    
    def _clean_text_for_search(self, text: str) -> str:
        """Clean text for consistent searching by removing punctuation and normalizing"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove common punctuation that causes search issues
        # Keep spaces, letters, numbers, but remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Normalize whitespace (multiple spaces become single space)
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
