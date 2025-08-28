import json
import re
import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This ensures output goes to console/terminal
        logging.FileHandler('search_debug.log')  # Also log to file for debugging
    ]
)

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
            # Use cleaned versions for indexing if available, otherwise clean the original
            owner = entry.get('owner_cleaned', self._clean_text_for_search(entry.get('owner', '')))
            pidn = entry.get('county_parcel_id_cleaned', self._clean_text_for_search(entry.get('county_parcel_id', '')))
            mailing = entry.get('mailing_address_cleaned', self._clean_text_for_search(entry.get('mail', '')))
            physical = entry.get('physical_address_cleaned', self._clean_text_for_search(entry.get('physical', '')))
            county = entry.get('county_cleaned', self._clean_text_for_search(entry.get('county', '')))
            
            # Debug: Log first few entries to see what we're working with
            if idx < 3:
                logger.info(f"🔍 Entry {idx}: county_parcel_id='{entry.get('county_parcel_id', 'MISSING')}', cleaned='{pidn}'")
            
            # Index by cleaned owner name
            if owner:
                self.owner_index[owner].append(idx)
                
                # Also index by words in owner name (using cleaned text)
                for word in owner.split():
                    if len(word) > 2:  # Only index words longer than 2 chars
                        self.word_index[word].append(idx)
            
            # Index by cleaned PIDN
            if pidn:
                # Debug: Log what we're indexing
                if idx < 5:  # Only log first few for debugging
                    logger.info(f"🔍 Indexing PIDN: '{pidn}' for entry {idx}")
                
                # Index the full PIDN
                self.parcel_index[pidn].append(idx)
                
                # Index without dashes
                pidn_no_dashes = pidn.replace('-', '')
                self.parcel_index[pidn_no_dashes].append(idx)
                
                # Index partial matches (both with and without dashes)
                for i in range(3, len(pidn) + 1):
                    partial = pidn[:i]
                    self.parcel_index[partial].append(idx)
                    
                    partial_no_dashes = partial.replace('-', '')
                    self.parcel_index[partial_no_dashes].append(idx)
            
            
            if physical:
                self.address_index[physical].append(idx)
                # Index by words in address (using cleaned text)
                
        
        logger.info(f"✅ Built indexes: {len(self.owner_index)} owners, {len(self.parcel_index)} parcels, {len(self.word_index)} words")
    
    def _fast_search(self, query: str) -> List[Dict[str, Any]]:
        """Fast search using pre-built indexes - now returns scored candidates"""
        query_lower = query.lower().strip()
        query_words = query_lower.split()

        # Debug logging
        logger.info(f"🔍 FAST SEARCH DEBUG - Query: '{query}' -> '{query_lower}'")
        logger.info(f"🔍 Query words: {query_words}")

        if "gans john" in query_lower:
            logger.info(f"🔍 DEBUG - Query words: {query_words}")
            logger.info(f"🔍 DEBUG - Owner index: {self.owner_index}")
            logger.info(f"🔍 DEBUG - Parcel index: {self.parcel_index}")
            logger.info(f"🔍 DEBUG - Address index: {self.address_index}")
            logger.info(f"🔍 DEBUG - Word index: {self.word_index}")
            
        # Get candidate indices from indexes
        candidates = set()
        
        # Check exact matches first (fastest)
        if query_lower in self.owner_index:
            candidates.update(self.owner_index[query_lower])
            logger.info(f"🔍 Found exact match '{query_lower}' in owner_index: {len(self.owner_index[query_lower])} entries")
        if query_lower in self.parcel_index:
            candidates.update(self.parcel_index[query_lower])
            logger.info(f"🔍 Found exact match '{query_lower}' in parcel_index: {len(self.parcel_index[query_lower])} entries")
        if query_lower in self.address_index:
            candidates.update(self.address_index[query_lower])
            logger.info(f"🔍 Found exact match '{query_lower}' in address_index: {len(self.address_index[query_lower])} entries")
        
        # Check word matches
        for word in query_words:
            if len(word) > 2 and word in self.word_index:
                word_candidates = self.word_index[word]
                candidates.update(word_candidates)
                logger.info(f"🔍 Found word '{word}' in word_index: {len(word_candidates)} entries")
        
        # SMART ADDRESS MATCHING (IMPROVED!)
        # Check if query looks like an address (has common address words)
        address_keywords = ['road', 'rd', 'street', 'st', 'avenue', 'ave', 'lane', 'ln', 'drive', 'dr', 'ranch', 'trail', 'way', 'circle', 'court', 'ct', 'blvd', 'highway', 'hwy', 'north', 'south', 'east', 'west', 'n', 's', 'e', 'w']
        is_likely_address = any(keyword in query_lower for keyword in address_keywords)

        # Also detect address patterns like "123 main street" or "hhr ranch road"
        has_number_pattern = bool(re.search(r'\d+', query_lower))
        has_address_pattern = len(query_words) >= 2 and any(keyword in query_lower for keyword in address_keywords)

        is_likely_address = is_likely_address or has_address_pattern

        # Debug: Log address detection
        logger.info(f"🔍 Address detection: is_likely_address={is_likely_address}")

        if is_likely_address and len(query_lower) >= 5:
            # Search for addresses containing the query as a substring
            address_matches = 0
            logger.info(f"🔍 Searching addresses for substring '{query_lower}'")
            
            # NORMALIZE the query for better matching (remove dashes, normalize spaces)
            normalized_query = re.sub(r'[^\w\s]', ' ', query_lower)  # Remove dashes and punctuation
            normalized_query = re.sub(r'\s+', ' ', normalized_query).strip()  # Normalize spaces
            
            for address_key in self.address_index.keys():
                # NORMALIZE the address key for comparison
                normalized_address = re.sub(r'[^\w\s]', ' ', address_key.lower())  # Remove dashes and punctuation
                normalized_address = re.sub(r'\s+', ' ', normalized_address).strip()  # Normalize spaces
                
                # Check if normalized address contains the normalized query
                if normalized_query in normalized_address:
                    candidates.update(self.address_index[address_key])
                    address_matches += 1
                    logger.info(f"🔍 Found address match {address_matches}: '{address_key}' -> normalized: '{normalized_address}'")
                    # Limit to prevent too many matches
                    if address_matches > 100:
                        break
            
            logger.info(f"🔍 Total address matches found: {address_matches}")
            
            # Also try matching individual words in addresses
            word_matches = 0
            logger.info(f"🔍 Also searching for individual address words...")
            for address_key in self.address_index.keys():
                normalized_address = re.sub(r'[^\w\s]', ' ', address_key.lower())
                normalized_address = re.sub(r'\s+', ' ', normalized_address).strip()
                
                # Check if all query words appear in the address
                if all(word in normalized_address for word in query_words):
                    candidates.update(self.address_index[address_key])
                    word_matches += 1
                    logger.info(f"🔍 Found word match {word_matches}: '{address_key}' contains all words")
                    if word_matches > 50:  # Limit word matches separately
                        break
            
            logger.info(f"🔍 Total word matches found: {word_matches}")
        
        # Add partial matches for parcel IDs (common search pattern)
        if len(query_lower) >= 3:
            for partial in range(3, len(query_lower) + 1):
                partial_query = query_lower[:partial]
                if partial_query in self.parcel_index:
                    partial_candidates = self.parcel_index[partial_query]
                    candidates.update(partial_candidates)
                    logger.info(f"🔍 Found partial parcel match '{partial_query}': {len(partial_candidates)} entries")
        
        logger.info(f"🔍 Total unique candidates found: {len(candidates)}")
        
        # Score the candidates using your new scoring system
        scored_candidates = []
        for entry_id in candidates:
            if entry_id < len(self.search_data):
                entry = self.search_data[entry_id]
                score = self._score_all_fields(entry, query_lower, query_words)
                scored_candidates.append({"entry": entry, "score": score})
        
        logger.info(f"�� Scored {len(scored_candidates)} candidates")
        
        return scored_candidates
    
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
        
        # Sort by score and filter out weak matches
        scored_results.sort(key=lambda x: x["score"], reverse=True)

        # FILTER: Only return results with score >= 150 (lowered from 300 to allow address matches)
        filtered_results = [result for result in scored_results if result["score"] >= 150]

        # Debug: Log top 5 scores for debugging
        if len(filtered_results) > 0:
            logger.info(f"🔍 Top 50 scores for query '{query}' (after filtering):")
            for i, result in enumerate(filtered_results[:50]):
                owner = result["entry"].get("owner", "Unknown")
                score = result["score"]
                logger.info(f"  {i+1}. Score {score}: {owner}")

        return [result["entry"] for result in filtered_results[:200]]
    
    def search(self, query: str, limit: Optional[int] = None, county_filter: Optional[List[str]] = None, field_filter: Optional[List[str]] = None, spatial_params: Optional[List[float]] = None, is_advanced: bool = False, search_fields: Optional[List[str]] = None, filters: Optional[Dict[str, Any]] = None, sort_options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Main search method - now handles both regular and advanced search"""
        
        if is_advanced:
            # Use advanced search
            return self.advanced_search(
                query=query,
                search_fields=search_fields or ['owner', 'physical_address', 'parcel_id'],
                limit=limit,
                filters=filters,
                sort_options=sort_options
            )
        else:
            # Use regular search (existing logic)
            query_lower = query.lower().strip()
            query_words = query_lower.split()
            
            logger.info(f"🔍 SEARCH: Query='{query}', county_filter={county_filter}, field_filter={field_filter}")
            
            # Initialize unstored results
            unstored_results = []
            
            # Apply county filter if provided (now expects county codes like teton_county_wy)
            if county_filter:
                filtered_data = []
                for entry in self.search_data:
                    # Extract county code from global_parcel_uid (e.g., "teton_county_wy_000001" -> "teton_county_wy")
                    uid = entry.get("GFI", "")
                    if uid and "_" in uid:
                        county_code = uid.split("_")[0] + "_" + uid.split("_")[1] + "_" + uid.split("_")[2]
                        if county_code in county_filter:
                            filtered_data.append(entry)
                
                if not filtered_data:
                    return []
                # Search within filtered data
                unstored_results = self._search_filtered(query, filtered_data, field_filter, spatial_params)
            else:
                # No county filter - use fast search for better performance
                logger.info(f" No county filter - using fast search for {len(self.search_data)} entries")
                unstored_results = self._fast_search(query)  # Already scored results!
                
                # No need to call _score_and_filter since _fast_search already scored them
            
            # Sort all results by score
            sorted_results = sorted(unstored_results, key=lambda x: x["score"], reverse=True)
            
            # Apply smart cutoff and return final results
            cutoff_results = self._apply_smart_cutoff(sorted_results, max_results=limit if limit else 200)        
            # Print top 5 results for debugging
            if len(cutoff_results) > 0:
                print(f"\n🔍 TOP 5 RESULTS for query '{query}':")
                for i, result in enumerate(cutoff_results[:5]):
                    owner = result["entry"].get("owner", "Unknown")
                    score = result["score"]
                    GFI = result["entry"].get("GFI", "No GFI")
                    physical = result["entry"].get("physical", "No address")
                    print(f"  {i+1}. Score {score}: {owner[:50]}... | Address: {physical[:50]}... | GFI: {GFI[:50]}...")
            else:
                print(f"\n🔍 NO RESULTS found for query '{query}'")
            
            # Extract just the entry objects for the frontend
            final_results = [result["entry"] for result in cutoff_results]
            
            return final_results
    
    def _search_filtered(self, query: str, filtered_data: List[Dict[str, Any]], field_filter: Optional[List[str]] = None, spatial_params: Optional[List[float]] = None) -> List[Dict[str, Any]]:
        """Search within filtered data - now returns scored candidates only"""
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        # ADD ADDRESS DETECTION FOR FILTERED SEARCHES TOO
        address_keywords = ['road', 'rd', 'street', 'st', 'avenue', 'ave', 'lane', 'ln', 'drive', 'dr', 'ranch', 'trail', 'way', 'circle', 'court', 'ct', 'blvd', 'highway', 'hwy']
        is_address_query = any(keyword in query_lower for keyword in address_keywords)
        
        logger.info(f"🔍 FILTERED SEARCH DEBUG - Query: '{query}' -> '{query_lower}'")
        logger.info(f"🔍 Is address query: {is_address_query}")
        logger.info(f"🔍 Query words: {query_words}")
        
        scored_candidates = []
        
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
            
            # Only include entries with positive scores
            if score > 0:
                scored_candidates.append({
                    "entry": entry,
                    "score": score
                })
        
        # Debug: Log top 50 scores for debugging
        if len(scored_candidates) > 0:
            logger.info(f"🔍 Top 50 scores for filtered query '{query}' (before cutoff):")
            for i, result in enumerate(scored_candidates[:50]):
                owner = result["entry"].get("owner", "Unknown")
                score = result["score"]
                logger.info(f"  {i+1}. Score {score}: {owner}")
        
        # Return scored candidates (main search will handle sorting and cutoff)
        return scored_candidates
    
    def _score_by_fields(self, entry: Dict[str, Any], query_lower: str, query_words: List[str], field_filter: List[str]) -> int:
        """Score entry based on specific fields only - USING SAME LOGIC AS MAIN SCORING"""
        score = 0
        
        # Get all searchable fields
        owner = entry.get("owner_cleaned", entry.get("owner", ""))
        parcel_id = entry.get("county_parcel_id_cleaned", entry.get("county_parcel_id", ""))
        tax_id = entry.get("tax_id", "")
        physical_address = entry.get('physical', '')
        mailing_address = entry.get('mail', '')  # Use 'mail' field from data
        
        # Normalize query for exact phrase matching
        normalized_query = re.sub(r'[^\w\s]', ' ', query_lower)
        normalized_query = re.sub(r'\s+', ' ', normalized_query).strip()
        
        # Check if ANY of the specified fields match (not all)
        for field in field_filter:
            field_lower = field.lower()
            field_score = 0
            
            if field_lower == "mailing_address":
                if mailing_address:
                    # DEBUG: Log what we're comparing for our test case
                    if "hhr ranch road" in query_lower or "Carlman" in entry.get('owner', ''):
                        print(f"🔍 DEBUG MAILING ADDRESS SCORING:")
                        print(f"  Query: '{query_lower}'")
                        print(f"  Normalized query: '{normalized_query}'")
                        print(f"  Mailing address: '{mailing_address}'")
                        print(f"  Owner: '{entry.get('owner', '')}'")
                    
                    # Check exact phrase match (HIGHEST PRIORITY)
                    phrase_regex = re.compile(f"\\b{re.escape(normalized_query)}\\b", re.IGNORECASE)
                    if phrase_regex.search(mailing_address):
                        field_score = 10000  # Boost from 1000 to 10000
                        print(f"  ✅ EXACT PHRASE MATCH: +10000 points!")
                    # Check if address contains the query as a substring (HIGH PRIORITY)
                    elif normalized_query.lower() in mailing_address.lower():
                        field_score = 5000  # New high-priority match
                        print(f"  ✅ SUBSTRING MATCH: +5000 points!")
                    else:
                        # Use percentage-based word matching like _score_field function
                        matching_words = 0
                        total_words = len(query_words)
                        
                        for word in query_words:
                            word_regex = re.compile(f"\\b{re.escape(word)}\\b", re.IGNORECASE)
                            if word_regex.search(mailing_address):
                                matching_words += 1
                        
                        # Calculate percentage and score accordingly
                        if matching_words > 0:
                            match_percentage = matching_words / total_words
                            
                            if match_percentage >= 0.8:  # 80%+ words match
                                field_score = 1000
                                print(f"  ✅ 80%+ WORDS MATCH ({matching_words}/{total_words}): +1000 points!")
                            elif match_percentage >= 0.6:  # 60%+ words match
                                field_score = 800
                                print(f"  ✅ 60%+ WORDS MATCH ({matching_words}/{total_words}): +800 points!")
                            elif match_percentage >= 0.4:  # 40%+ words match
                                field_score = 600
                                print(f"  ✅ 40%+ WORDS MATCH ({matching_words}/{total_words}): +600 points!")
                            elif match_percentage >= 0.2:  # 20%+ words match
                                field_score = 400
                                print(f"  ✅ 20%+ WORDS MATCH ({matching_words}/{total_words}): +400 points!")
                            else:  # Less than 20% words match
                                field_score = 200
                                print(f"  ✅ <20% WORDS MATCH ({matching_words}/{total_words}): +200 points!")
                        else:
                            field_score = 0
                            print(f"  ❌ NO WORD MATCHES: 0 points")
                    
                    print(f"  Final field score: {field_score}")
                    
                    # Use the highest score from any matching field
                    if field_score > score:
                        score = field_score
            
            elif field_lower == "owner":
                # Use cleaned version for searching
                if owner:
                    # Check exact phrase match
                    phrase_regex = re.compile(f"\\b{re.escape(normalized_query)}\\b", re.IGNORECASE)
                    if phrase_regex.search(owner):
                        field_score = 500
                    # Check all words as whole words
                    elif all(re.compile(f"\\b{re.escape(word)}\\b", re.IGNORECASE).search(owner) for word in query_words):
                        field_score = 250
                    # Check some words as exact matches
                    elif any(re.compile(f"\\b{re.escape(word)}\\b", re.IGNORECASE).search(owner) for word in query_words):
                        field_score = 100
                    # Check partial matches
                    elif any(word in owner.lower() for word in query_words):
                        field_score = 10
                    
                    # Add field boost
                    field_score += 100
                    
            elif field_lower == "pidn":
                if parcel_id:
                    # Check exact phrase match
                    phrase_regex = re.compile(f"\\b{re.escape(normalized_query)}\\b", re.IGNORECASE)
                    if phrase_regex.search(parcel_id):
                        field_score = 500
                    # Check all words as whole words
                    elif all(re.compile(f"\\b{re.escape(word)}\\b", re.IGNORECASE).search(parcel_id) for word in query_words):
                        field_score = 250
                    # Check some words as exact matches
                    elif any(re.compile(f"\\b{re.escape(word)}\\b", re.IGNORECASE).search(parcel_id) for word in query_words):
                        field_score = 100
                    # Check partial matches
                    elif any(word in parcel_id.lower() for word in query_words):
                        field_score = 10
                    
            elif field_lower == "physical_address":
                if physical_address:
                    # ✅ NORMALIZE the physical address field like regular search does
                    normalized_physical = physical_address.replace('-', '')  # ✅ Remove hyphens
                    normalized_physical = re.sub(r'[^\w\s]', ' ', normalized_physical.lower())
                    normalized_physical = re.sub(r'\s+', ' ', normalized_physical).strip()
                    
                    if "ranch road" in normalized_physical:
                        print(f"🔍 DEBUG PHYSICAL ADDRESS SCORING:")
                        print(f"  Query: '{query_lower}'")
                        print(f"  Normalized query: '{normalized_query}'")
                        print(f"  Physical address: '{normalized_physical}'")
                        print(f"  Owner: '{entry.get('owner', '')}'")
                        print(f"  Physical address: '{physical_address}'")
                    
                    # Check exact phrase match (HIGHEST PRIORITY)
                    phrase_regex = re.compile(f"\\b{re.escape(normalized_query)}\\b", re.IGNORECASE)
                    if phrase_regex.search(normalized_physical):
                        field_score = 10000
                        print(f"  ✅ EXACT PHRASE MATCH: +10000 points!")
                    # Check if address contains the query as a substring (HIGH PRIORITY)
                    elif normalized_query.lower() in normalized_physical.lower():
                        field_score = 5000
                        print(f"  ✅ SUBSTRING MATCH: +5000 points!")
                    else:
                        # Use percentage-based word matching
                        matching_words = 0
                        total_words = len(query_words)
                        
                        for word in query_words:
                            word_regex = re.compile(f"\\b{re.escape(word)}\\b", re.IGNORECASE)
                            if word_regex.search(normalized_physical):
                                matching_words += 1
                        
                        # Calculate percentage and score accordingly
                        if matching_words > 0:
                            match_percentage = matching_words / total_words
                            
                            if match_percentage >= 0.8:  # 80%+ words match
                                field_score = 400
                            elif match_percentage >= 0.6:  # 60%+ words match
                                field_score = 300
                            elif match_percentage >= 0.4:  # 40%+ words match
                                field_score = 200
                            elif match_percentage >= 0.2:  # 20%+ words match
                                field_score = 100
                            else:  # Less than 20% words match
                                field_score = 50
                        else:
                            field_score = 0
                   
                    
                    # Use the highest score from any matching field
                    if field_score > score:
                        score = field_score
            
            
            
            # Use the highest score from any matching field
            score = max(score, field_score)
        
        return score
    
    def _score_all_fields(self, entry: Dict[str, Any], query_lower: str, query_words: List[str]) -> int:
        """Score entry across all searchable fields with category-based scoring"""
      
        
        # 1. QUERY CLASSIFICATION - Determine what type of search this is
        query_type = self._classify_query(query_lower, query_words)
        
        # 2. INITIALIZE CATEGORY SCORES
        scores = {
            'owner': 0,
            'parcel_id': 0,
            'physical_address': 0
        }
        
        # 3. GET AND NORMALIZE FIELDS
        owner = entry.get("owner_cleaned", entry.get("owner", ""))
        parcel_id = entry.get("county_parcel_id_cleaned", entry.get("county_parcel_id", ""))
        physical_address = entry.get('physical', '')
       
        
        # Normalize address fields for better matching
        if physical_address:
            physical_address = physical_address.replace('-', '')  # "H-H-R" → "HHR"
        
        # Normalize query for exact phrase matching
        normalized_query = re.sub(r'[^\w\s]', ' ', query_lower)
        normalized_query = re.sub(r'\s+', ' ', normalized_query).strip()
        
        
        
        # 4. SCORE EACH CATEGORY SEPARATELY
        
        # OWNER SCORING
        if owner:
            owner_score = self._score_field(owner, query_lower, query_words, normalized_query, 'owner')
            scores['owner'] = owner_score
        
        # PARCEL ID SCORING  
        if parcel_id:
            parcel_score = self._score_field(parcel_id, query_lower, query_words, normalized_query, 'parcel_id')
            scores['parcel_id'] = parcel_score
        
        # PHYSICAL ADDRESS SCORING
        if physical_address:
            address_score = self._score_field(physical_address, query_lower, query_words, normalized_query, 'physical_address')
            scores['physical_address'] = address_score
        
        # 5. APPLY QUERY-TYPE BOOSTS
        if query_type == 'address':
            # Address queries get boosted address scores
            scores['physical_address'] = int(scores['physical_address'] * 1.5)
        elif query_type == 'owner':
            # Owner queries get boosted owner scores
            scores['owner'] = int(scores['owner'] * 1.5)
        elif query_type == 'parcel_id':
            # PIDN queries get boosted parcel_id scores
            scores['parcel_id'] = int(scores['parcel_id'] * 1.5)
        
        # 6. CALCULATE FINAL SCORE (weighted by query type)
        final_score = self._calculate_final_score(scores, query_type)
        
        
        
        return final_score
    
    def _classify_query(self, query_lower: str, query_words: List[str]) -> str:
        """Classify query type: address, owner, parcel_id, or unknown"""
        
        # Check if it's a PIDN (mostly numbers/identifiers)
        numeric_chars = sum(1 for char in query_lower if char.isdigit())
        if numeric_chars >= len(query_lower) * 0.6:  # 60%+ numeric
            return 'parcel_id'
        
        # Check if it's an address query
        address_keywords = ['road', 'rd', 'street', 'st', 'avenue', 'ave', 'lane', 'ln', 
                           'drive', 'dr', 'ranch', 'trail', 'way', 'circle', 'court', 'ct', 
                           'blvd', 'highway', 'hwy', 'loop', 'place', 'pl']
        if any(keyword in query_lower for keyword in address_keywords):
            return 'address'
        
        # Check if it looks like an owner name (has common name patterns)
        name_patterns = ['&', 'and', 'trust', 'llc', 'inc', 'corp', 'company', 'co']
        if any(pattern in query_lower for pattern in name_patterns):
            return 'owner'
        
        # Default to unknown (treat owner/address similarly)
        return 'unknown'
    
    def _score_field(self, field_value: str, query_lower: str, query_words: List[str], 
                     normalized_query: str, field_type: str) -> int:
        """Score a single field with percentage-based word matching"""
        
        field_lower = field_value.lower()
        score = 0
        
        # 1. EXACT PHRASE MATCH (500 points)
        phrase_regex = re.compile(f"\\b{re.escape(normalized_query)}\\b", re.IGNORECASE)
        if phrase_regex.search(field_lower):
            score += 1000
            return score  # Exact match gets max score
        
        # 2. PERCENTAGE-BASED WORD MATCHING
        matching_words = 0
        total_words = len(query_words)
        
        for word in query_words:
            word_regex = re.compile(f"\\b{re.escape(word)}\\b", re.IGNORECASE)
            if word_regex.search(field_lower):
                matching_words += 1
        # Debug: Print scores for specific addresses and queries
        # Only print if the field_value is "H-H-R RANCH ROAD" or "TWIN CREEK RANCH ROAD"
        # and the query is "hhr ranch road"
       
        # Calculate percentage and score accordingly
        if matching_words > 0:
            match_percentage = matching_words / total_words
            
            if match_percentage >= 0.8:  # 80%+ words match
                score += 400
            elif match_percentage >= 0.6:  # 60%+ words match
                score += 300
            elif match_percentage >= 0.4:  # 40%+ words match
                score += 200
            elif match_percentage >= 0.2:  # 20%+ words match
                score += 100
            else:  # Less than 20% words match
                score += 50
        #print(f"field_value: {field_value}")
        if 'HHR' in field_value:
            print(f"DEBUG SCORE: field_type={field_type}, field_lower='{field_lower}', field_value='{field_value}', query='{query_lower}'")
            print(f"  matching_words={matching_words}, total_words={total_words}")
            if matching_words > 0:
                print(f"  match_percentage={matching_words/total_words}")
            else:
                print("  match_percentage=0 (no matching words)")
            print(f"  Score after phrase/word matching: {score}")
        
        if field_type == 'owner' and field_value:
            score += 50  # Owner field relevance
        elif field_type == 'physical_address' and field_value:
            score += 50  # Address field relevance
        elif field_type == 'parcel_id' and field_value:
            score += 50  # Parcel ID field relevance
        return score
    
    def _calculate_final_score(self, scores: Dict[str, int], query_type: str) -> int:
        """Calculate final score with query-type weighting"""
        
        # Base score is sum of all category scores
        base_score = sum(scores.values())
        
        # Apply query-type weighting
        if query_type == 'address':
            # Address queries: prioritize address matches
            return base_score + (scores['physical_address'] * 0.3)
        elif query_type == 'owner':
            # Owner queries: prioritize owner matches
            return base_score + (scores['owner'] * 0.3)
        elif query_type == 'parcel_id':
            # PIDN queries: prioritize parcel_id matches
            return base_score + (scores['parcel_id'] * 0.3)
        else:
            # Unknown type: no additional weighting
            return base_score
    
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
        text_fields = ['owner', 'county_parcel_id', 'mail', 'physical', 'county']
        
        for entry in data:
            for field in text_fields:
                if field in entry and entry[field]:
                    # Store original value
                    original = entry[field]
                    
                    # Create cleaned version for searching
                    cleaned = self._clean_text_for_search(original)
                    
                    # Store cleaned version for indexing/searching
                    entry[f"{field}_cleaned"] = cleaned
                    # Keep original value in main field for display
                    # entry[field] remains unchanged
        
        logger.info("✅ Data pre-cleaning completed")
        return data
    
    def _clean_text_for_search(self, text: str) -> str:
        """Clean text for consistent searching by removing punctuation and normalizing"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # For PIDN fields, preserve dashes and numbers
        if any(char.isdigit() for char in text):
            # This looks like a PIDN - preserve dashes and numbers
            text = re.sub(r'[^\w\s\-]', ' ', text)  # Keep dashes
        else:
            # Regular text - remove punctuation
            text = re.sub(r'[^\w\s]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text 

    def _apply_smart_cutoff(self, scored_results: List[Dict], max_results: int = 200) -> List[Dict]:
        """Smart cutoff that looks for natural score gaps"""
        if not scored_results:
            return []
        
        # Sort by score descending
        sorted_results = sorted(scored_results, key=lambda x: x["score"], reverse=True)
        
        # Look for significant score drops (gaps)
        cutoff_index = max_results  # Default to max_results
        
        for i in range(1, min(len(sorted_results), max_results + 50)):
            current_score = sorted_results[i]["score"]
            prev_score = sorted_results[i-1]["score"]
            
            # If there's a big score drop (>50%), that's a natural cutoff
            if prev_score > 0 and (prev_score - current_score) / prev_score > 0.5:
                cutoff_index = i
                break
        
        filtered_results = sorted_results[:cutoff_index]
        
        logger.info(f"🔍 Smart cutoff: kept top {len(filtered_results)} results (cutoff at score {filtered_results[-1]['score']})")
        
        return filtered_results 



    def advanced_search(self, 
                       query: str,
                       search_fields: List[str],           
                       limit: Optional[int] = None,
                       filters: Dict[str, Any] = None,     
                       sort_options: Dict[str, Any] = None 
    ) -> List[Dict[str, Any]]:
        """
        Advanced search with field-specific control
        """
        try:
            # Handle missing or empty search_fields
            if not search_fields or len(search_fields) == 0:
                # Default to searching all fields if none specified
                search_fields = ['owner', 'physical_address', 'parcel_id', 'mailing_address', 'county']
                logger.info(f"🔍 No search fields specified, defaulting to: {search_fields}")
            
            query_lower = query.lower().strip()
            query_words = query_lower.split()
            
            logger.info(f"🔍 ADVANCED SEARCH: Query='{query}', fields={search_fields}, filters={filters}")
            
            # Initialize results
            all_results = []
            total_entries_processed = 0
            total_entries_filtered = 0
            total_entries_scored = 0
            
            # Get all entries (no fast search for advanced search)
            for entry in self.search_data:
                total_entries_processed += 1
                
                # Add this right after getting an entry
                if total_entries_processed <= 5:  # Only log first 5 entries
                    print(f"🔍 Entry fields: {list(entry.keys())}")
                    print(f"🔍 Mail field: '{entry.get('mail', 'NOT_FOUND')}'")
                    print(f"🔍 Mailing address field: '{entry.get('mailing_address', 'NOT_FOUND')}'")
                
                # Apply filters first
                if filters:
                    if not self._passes_filters(entry, filters):
                        total_entries_filtered += 1
                        continue
                
                # Score using only specified fields
                score = self._score_by_fields(entry, query_lower, query_words, search_fields)
                
                if score > 0:
                    all_results.append({"entry": entry, "score": score})
                    total_entries_scored += 1
            
            logger.info(f"🔍 ADVANCED SEARCH DEBUG: Processed {total_entries_processed} entries, filtered out {total_entries_filtered}, scored {total_entries_scored} with score > 0")
            
            # Sort results
            if sort_options and sort_options.get('field') != 'score':
                # Sort by specified field instead of score
                sort_field = sort_options['field']
                reverse = sort_options.get('order', 'desc') == 'desc'
                all_results.sort(key=lambda x: x["entry"].get(sort_field, ''), reverse=reverse)
            else:
                # Default sort by score
                all_results.sort(key=lambda x: x["score"], reverse=True)
            
            # Apply limit or smart cutoff
            if limit and limit > 0:
                final_results = all_results[:limit]
                logger.info(f"🔍 Advanced search: returning top {len(final_results)} results (limit specified)")
            else:
                final_results = self._apply_smart_cutoff(all_results)
                logger.info(f"🔍 Advanced search: returning {len(final_results)} results (gap-based cutoff)")
            
            # Print top 5 results for debugging
            if len(final_results) > 0:
                print(f"\n🔍 ADVANCED SEARCH TOP 5 RESULTS for query '{query}':")
                for i, result in enumerate(final_results[:5]):
                    owner = result["entry"].get("owner", "Unknown") or "Unknown"
                    score = result["score"]
                    physical = result["entry"].get("physical", "No address") or "No address"
                    print(f"  {i+1}. Score {score}: {owner[:50]}... | Address: {physical[:50]}...")
            else:
                print(f"\n🔍 ADVANCED SEARCH: NO RESULTS found for query '{query}'")
                # Debug: Show a few sample entries and their scores
                if len(all_results) > 0:
                    print(f"🔍 DEBUG: Found {len(all_results)} entries with scores, but they were filtered out")
                    for i, result in enumerate(all_results[:3]):
                        owner = result["entry"].get("owner", "Unknown") or "Unknown"
                        score = result["score"]
                        print(f"  Sample entry {i+1}: Score {score}, Owner: {owner[:50]}...")
                else:
                    print(f"🔍 DEBUG: No entries scored above 0. This suggests a scoring issue.")
            
            return [result["entry"] for result in final_results]
            
        except Exception as e:
            logger.error(f"🔍 ADVANCED SEARCH ERROR: {e}")
            import traceback
            logger.error(f" ADVANCED SEARCH TRACEBACK: {traceback.format_exc()}")
            raise e
    
    def _passes_filters(self, entry: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if entry passes all specified filters"""
        for filter_type, filter_value in filters.items():
            # Skip empty/false filters
            if filter_value is None or filter_value == "" or filter_value == []:
                continue
            if filter_type == 'has_physical_address' and filter_value is False:
                continue  # Don't filter if user doesn't want physical addresses
            
            if filter_type == 'county':
                # Only apply if counties are actually specified
                if filter_value and len(filter_value) > 0:
                    uid = entry.get("GFI", "")
                    if uid and "_" in uid:
                        county_code = uid.split("_")[0] + "_" + uid.split("_")[1] + "_" + uid.split("_")[2]
                        if county_code not in filter_value:
                            return False
                    else:
                        return False
                else:
                    continue
            
            elif filter_type == 'min_score':
                # This will be applied after scoring
                pass
            
            elif filter_type == 'has_physical_address':
                if filter_value and not entry.get('physical'):
                    return False
            
            elif filter_type == 'owner_type':
                # FIX: Handle None values properly
                owner = entry.get('owner', '')
                if owner is None:
                    owner = ''
                owner = owner.lower()
                
                if filter_value == 'individual':
                    # Check if owner looks like an individual (not business/trust)
                    business_indicators = ['llc', 'inc', 'corp', 'company', 'trust', 'partnership']
                    if any(indicator in owner for indicator in business_indicators):
                        return False
                elif filter_value == 'business':
                    # Check if owner looks like a business
                    business_indicators = ['llc', 'inc', 'corp', 'company', 'partnership']
                    if not any(indicator in owner for indicator in business_indicators):
                        return False
        
        return True 
