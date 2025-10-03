"""Property details scraper with domain-based routing, extensible class, and robust helpers."""
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
import json
import copy
from pathlib import Path
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

class GeneralPropertyDetailsScraper:
    """
    General, robust property details scraper. Can be subclassed or overridden for county-specific logic.
    """
    def __init__(self, url: str, config: dict = None):
        self.url = url
        self.config = config or {}
        self.soup = None
        self.raw_tables = None
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        self.county = self.get_county_from_url()

    def get_county_from_url(self) -> str:
        """Extract a county name from the URL for file naming."""
        # Try to extract county from the domain or path
        match = re.search(r'(sublette|fremont|lincoln)', self.url, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return 'unknown_county'

    def write_html_to_file(self, html: str):
        """Write the raw HTML to a file named by county and timestamp."""
        # Disabled for mass collection to avoid file clutter
        pass

    def write_tables_to_file(self, tables: dict):
        """Write the extracted tables to a JSON file named by county and timestamp."""
        # Disabled for mass collection to avoid file clutter
        pass

    def write_filled_json(self, filled: dict):
        """Write the filled canonical structure to a JSON file named by county and timestamp."""
        # Disabled for mass collection to avoid file clutter
        pass

    def fetch(self):
        """Fetch the page and parse with BeautifulSoup. Writes raw HTML to a file for debugging."""
        logger.info("(General Property Details) Starting property details scrape")
        resp = requests.get(self.url, timeout=10)
        resp.raise_for_status()
        self.write_html_to_file(resp.text)
        self.soup = BeautifulSoup(resp.text, 'html.parser')
        logger.info("(General Property Details) Fetched and parsed HTML")

    def extract_all_tables_and_lists(self) -> dict:
        """Extracts all tables and definition lists as thoroughly as possible, including nested tables, without mixing parent and child rows."""
        logger.debug("(General Property Details) Extracting tables and lists")
        results = {}
        if not self.soup:
            return results
        
        # NEW: Extract span-based content with better heuristics FIRST
        span_data = {}
        for span in self.soup.find_all('span'):
            text = span.get_text(' ', strip=True)
            if text and len(text) > 2:  # Only meaningful spans
                # Better address detection
                if any(word in text.upper() for word in ['ST', 'DR', 'AVE', 'ROAD', 'STREET', 'NORTH', 'SOUTH', 'EAST', 'WEST']):
                    if 'property_address' not in span_data:
                        span_data['property_address'] = text
                # Better owner detection
                elif any(word in text.upper() for word in ['TRUSTEE', 'TRUST', 'LLC', 'INC', 'CORP', 'COMPANY']):
                    if 'owner_name' not in span_data:
                        span_data['owner_name'] = text
                # Percent ownership
                elif text.endswith('%'):
                    span_data['percent_ownership'] = text
                # ZIP codes
                elif text.isdigit() and len(text) == 5:
                    span_data['zip_code'] = text
                # State codes
                elif text.upper() in ['WY', 'WYOMING']:
                    span_data['state'] = text
        
        # NEW: Extract div content that might contain key info
        div_data = {}
        for div in self.soup.find_all('div', class_=['ibox-content', 'col-6', 'col']):
            text = div.get_text(' ', strip=True)
            if text and len(text) > 10:
                # Look for address patterns
                if any(word in text.upper() for word in ['STREET', 'ADDRESS', 'ROAD']):
                    div_data['address_section'] = text
                # Look for owner patterns
                elif any(word in text.upper() for word in ['OWNER', 'TRUSTEE', 'TRUST']):
                    div_data['owner_section'] = text
        
        # NEW: Extract strong tags (often contain labels)
        strong_data = {}
        for strong in self.soup.find_all('strong'):
            text = strong.get_text(' ', strip=True)
            if text and len(text) > 2:
                # Get the next sibling text as the value
                next_sibling = strong.find_next_sibling()
                if next_sibling:
                    value = next_sibling.get_text(' ', strip=True)
                    if value:
                        strong_data[text] = value
        
        # NEW: Extract p tags that might contain extended legal descriptions
        p_data = {}
        for p in self.soup.find_all('p'):
            text = p.get_text(' ', strip=True)
            if text and len(text) > 10:
                if 'EXTENDED LEGAL' in text.upper() or 'LEGAL DESCRIPTION' in text.upper():
                    p_data['extended_legal'] = text
        
        # Extract tables (existing logic) with better debugging
        tables = self.soup.find_all('table')
        logger.debug(f"(General Property Details) Found {len(tables)} tables in the HTML")
        table_idx = 0
        for table in tables:
            table_idx += 1
            logger.debug(f"(General Property Details) Processing table {table_idx}")
            rows = []
            headers = []
            
            # Get all rows in this table
            table_rows = table.find_all('tr', recursive=False)
            logger.debug(f"(General Property Details) Table {table_idx} has {len(table_rows)} rows")
            
            for i, row in enumerate(table_rows):
                cells = row.find_all(['td', 'th'], recursive=False)
                logger.debug(f"(General Property Details) Row {i} has {len(cells)} cells")
                
                # Header row: more than 2 cells, or first row, or has th elements
                if (i == 0 and len(cells) > 2) or (row.get('class') and 'toprow' in row.get('class', [])) or any(cell.name == 'th' for cell in cells):
                    headers = [c.get_text(' ', strip=True) for c in cells]
                    logger.debug(f"(General Property Details) Headers: {headers}")
                    continue
                
                # Data row with headers
                if headers and len(cells) == len(headers):
                    row_data = {h: c.get_text(' ', strip=True) for h, c in zip(headers, cells)}
                    rows.append(row_data)
                    logger.debug(f"(General Property Details) Data row: {row_data}")
                # Key-value row
                elif len(cells) == 2:
                    key = cells[0].get_text(' ', strip=True)
                    value = cells[1].get_text(' ', strip=True)
                    rows.append({key: value})
                    logger.debug(f"(General Property Details) Key-value row: {key} = {value}")
                # Feature/note row
                elif len(cells) == 1:
                    value = cells[0].get_text(' ', strip=True)
                    rows.append({'note': value})
                    logger.debug(f"(General Property Details) Note row: {value}")
                # Multi-column row without headers
                elif len(cells) > 2:
                    # Create a simple list of values
                    values = [c.get_text(' ', strip=True) for c in cells]
                    rows.append({'values': values})
                    logger.debug(f"(General Property Details) Multi-column row: {values}")
            
            if rows:
                results[f'table_{table_idx}'] = rows
                logger.debug(f"(General Property Details) Added table_{table_idx} with {len(rows)} rows")
        
        # Extract all <dl> blocks
        dl_idx = 0
        for dl in self.soup.find_all('dl'):
            dl_idx += 1
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            dl_data = {}
            for dt, dd in zip(dts, dds):
                key = dt.get_text(' ', strip=True)
                value = dd.get_text(' ', strip=True)
                dl_data[key] = value
            if dl_data:
                results[f'dl_{dl_idx}'] = dl_data
        
        # Combine all extracted data with spans first
        if span_data:
            results['spans'] = span_data
        if div_data:
            results['divs'] = div_data
        if strong_data:
            results['strong_tags'] = strong_data
        if p_data:
            results['p_tags'] = p_data
        
        logger.debug(f"(General Property Details) Extracted data from {len(results)} sources")
        return results

    def normalize_key(self, k):
        # Remove non-breaking spaces, colons, extra whitespace, make lowercase
        k = re.sub(r'[\xa0\s]+', ' ', k)
        k = k.replace(':', '').strip().lower()
        return k

    def map_to_canonical(self, raw_tables: dict) -> dict:
        """Maps raw table data to a canonical JSON structure defined in structure.json."""
        logger.debug("(General Property Details) Mapping to canonical structure")
        # Load canonical structure
        structure_path = Path(__file__).parent.parent / 'structure.json'
        try:
            with open(structure_path) as f:
                canonical = json.load(f)
        except FileNotFoundError:
            # Try absolute path
            structure_path = Path(__file__).parent.parent.parent / 'property_info_api' / 'structure.json'
            with open(structure_path) as f:
                canonical = json.load(f)
    
        result = copy.deepcopy(canonical)
        developments = []
        in_development_section = False
        current_dev = None
        
        # Define field patterns for mapping
        field_patterns = {
            'county_parcel_id': [r'parcel.*id', r'pidn', r'county.*parcel'],
            'tax_id': [r'tax.*id', r'account.*number'],
            'owner_name': [r'owner', r'name'],
            'physical_address': [r'street.*address', r'physical.*address', r'property.*address'],
            'mailing_address': [r'mailing.*address', r'mail.*address'],
            'total_acres': [r'total.*acre', r'acres?$', r'acre.*total'],
            'legal.location': [r'legal.*description', r'location', r'legal.*location'],
            'deed': [r'deed', r'document'],
            'value_summary.total_value': [r'total.*value', r'actual.*value'],
            'value_summary.land': [r'land.*value'],
            'value_summary.developments': [r'improvement.*value', r'building.*value', r'development.*value']
        }
        
        # Process all data sources (tables, dl, spans, divs, etc.)
        for source_name, source_data in raw_tables.items():
            logger.debug(f"(General Property Details) Processing {source_name}")
            
            # Handle different data source types
            if source_name.startswith('table_') or source_name.startswith('dl_'):
                # Process table/dl data as before
                for row in source_data:
                    logger.debug(f"(General Property Details) Row: {row}")
                    matched = False
                    
                    # NEW: Handle value information tables
                    if isinstance(row, dict) and 'Value Type' in row:
                        logger.debug(f"(General Property Details) Found value table row: {row}")
                        value_type = row.get('Value Type', '')
                        appraised_value = row.get('Appraised Value', '')
                        if value_type and appraised_value:
                            if 'land' in value_type.lower():
                                result['value_summary']['land'] = appraised_value
                                logger.debug(f"(General Property Details) Matched land value: {appraised_value}")
                                matched = True
                            elif 'improvement' in value_type.lower():
                                result['value_summary']['developments'] = appraised_value
                                logger.debug(f"(General Property Details) Matched improvement value: {appraised_value}")
                                matched = True
                    
                    # Detect start of a development/building section
                    if isinstance(row, dict) and any(
                        self.normalize_key(key) in ["building id", "residential", "out building", "development", "building_id"]
                        for key in row.keys()
                    ):
                        if current_dev:
                            developments.append(current_dev)
                        current_dev = copy.deepcopy(canonical['developments'][0])
                        in_development_section = True
                        logger.debug("(General Property Details) Detected start of development section")
                    if in_development_section and current_dev:
                        # Fill development fields
                        for k, v in row.items():
                            norm_k = self.normalize_key(k)
                            logger.debug(f"(General Property Details) Key: {k} (norm: {norm_k}), Value: {v}")
                            if re.search(r'building id|building_id', norm_k):
                                current_dev['building_id'] = v
                                logger.debug(f"(General Property Details) Matched to development building_id")
                            if re.search(r'residential|type|out building|development', norm_k):
                                current_dev['type'] = v
                                logger.debug(f"(General Property Details) Matched to development type")
                            if re.search(r'year built', norm_k):
                                current_dev['attributes']['year_built'] = v
                                logger.debug(f"(General Property Details) Matched to development year_built")
                            if re.search(r'sq ft', norm_k):
                                current_dev['attributes']['sq_ft'] = v
                                logger.debug(f"(General Property Details) Matched to development sq_ft")
                            if re.search(r'bedroom', norm_k):
                                current_dev['attributes']['bedrooms'] = v
                                logger.debug(f"(General Property Details) Matched to development bedrooms")
                            if re.search(r'bath', norm_k):
                                current_dev['attributes']['baths'] = v
                                logger.debug(f"(General Property Details) Matched to development baths")
                    else:
                        # Fill top-level fields
                        for k, v in row.items():
                            norm_k = self.normalize_key(k)
                            logger.debug(f"(General Property Details) Key: {k} (norm: {norm_k}), Value: {v}")
                            for field, patterns in field_patterns.items():
                                for pat in patterns:
                                    if re.search(pat, norm_k):
                                        # Support nested fields
                                        if '.' in field:
                                            parent, child = field.split('.')
                                            result[parent][child] = v
                                        else:
                                            result[field] = v
                                        logger.debug(f"(General Property Details) Matched to {field} (pattern: {pat})")
                                        matched = True
                                        break
                                if matched:
                                    break
                        if not matched:
                            logger.debug(f"(General Property Details) No match for this row.")
            
            elif source_name == 'spans':
                # Process span data
                logger.debug(f"(General Property Details) Processing spans: {source_data}")
                for k, v in source_data.items():
                    logger.debug(f"(General Property Details) Key: {k}, Value: {v}")
                    if k == 'property_address':
                        result['physical_address'] = v
                        logger.debug(f"(General Property Details) Matched to physical_address")
                    elif k == 'owner_name':
                        result['owner_name'] = v
                        logger.debug(f"(General Property Details) Matched to owner_name")
                    elif k == 'percent_ownership':
                        # Store as additional info
                        logger.debug(f"(General Property Details) Found percent_ownership: {v}")
            
            elif source_name == 'divs':
                # Process div data
                logger.debug(f"(General Property Details) Processing divs: {source_data}")
                for k, v in source_data.items():
                    logger.debug(f"(General Property Details) Key: {k}, Value: {v}")
                    # Try to extract addresses from div content
                    if 'address' in k.lower():
                        # Look for address patterns in the text
                        address_match = re.search(r'(\d+\s+[A-Z\s]+(?:ST|DR|AVE|ROAD|STREET))', v, re.IGNORECASE)
                        if address_match and not result['physical_address']:
                            result['physical_address'] = address_match.group(1).strip()
                            logger.debug(f"(General Property Details) Extracted physical_address from div")
                    elif 'owner' in k.lower():
                        # Look for owner patterns in the text
                        owner_match = re.search(r'([A-Z\s&]+(?:TRUSTEE|TRUST|LLC|INC))', v, re.IGNORECASE)
                        if owner_match and not result['owner_name']:
                            result['owner_name'] = owner_match.group(1).strip()
                            logger.debug(f"(General Property Details) Extracted owner_name from div")
            
            elif source_name == 'strong_tags':
                # Process strong tag data
                logger.debug(f"(General Property Details) Processing strong tags: {source_data}")
                for k, v in source_data.items():
                    logger.debug(f"(General Property Details) Key: {k}, Value: {v}")
                    norm_k = self.normalize_key(k)
                    for field, patterns in field_patterns.items():
                        for pat in patterns:
                            if re.search(pat, norm_k):
                                if '.' in field:
                                    parent, child = field.split('.')
                                    result[parent][child] = v
                                else:
                                    result[field] = v
                                logger.debug(f"(General Property Details) Matched to {field} (pattern: {pat})")
                                break
            
            elif source_name == 'p_tags':
                # Process p tag data
                logger.debug(f"(General Property Details) Processing p tags: {source_data}")
                for k, v in source_data.items():
                    logger.debug(f"(General Property Details) Key: {k}, Value: {v}")
                    if 'extended_legal' in k.lower():
                        result['legal']['extended'] = v
                        logger.debug(f"(General Property Details) Matched to legal.extended")
        
        if current_dev:
            developments.append(current_dev)
        # Remove empty developments
        result['developments'] = [d for d in developments if any(v for v in d['attributes'].values())]
        logger.debug(f"(General Property Details) Mapped to canonical structure with {len(result['developments'])} developments")
        return result

    def scrape(self) -> dict:
        """Driver method to fetch and extract property details."""
        self.fetch()
        raw_tables = self.extract_all_tables_and_lists()
        self.write_tables_to_file(raw_tables)
        filled = self.map_to_canonical(raw_tables)
        self.write_filled_json(filled)
        logger.info("(General Property Details) Completed property details scrape")
        return filled

def scrape_property_details(url: str, config: dict = None) -> dict:
    """Instantiate and use the appropriate PropertyDetailsScraper based on the URL and county."""
    logger.info(f"(General Property Details) Starting property details scrape for County: {config['county'].lower()}")
    
    # Get county from config if available
    county = None
    if config and 'county' in config:
        county = config['county'].lower()
    
    logger.debug(f"(General Property Details) URL = {url}")
    logger.debug(f"(General Property Details) County = {county}")
    
    # Check if this is a Greenwood county URL or if county is Fremont/Sublette
    use_greenwood = (
        'greenwood' in url.lower() or 
        'maps.greenwoodmap.com' in url.lower() or
        county in ['fremont_county_wy', 'sublette_county_wy']
    )
    use_lincoln = (
        'lincoln' in url.lower() or
        county in ['lincoln_county_wy']
    )
    use_teton_idaho = (
        'tetonidaho' in url.lower() or
        'tetonidaho.maps.arcgis.com' in url.lower() or
        county in ['teton_county_id']
    )
    use_teton = (
        ('teton' in url.lower() and 'tetonidaho' not in url.lower()) or
        'tetoncountywy.gov' in url.lower() or
        county in ['teton_county_wy']
    )
    
    logger.debug(f"(General Property Details) Use Greenwood = {use_greenwood}")
    logger.debug(f"(General Property Details) Use Lincoln = {use_lincoln}")
    logger.debug(f"(General Property Details) Use Teton = {use_teton}")
    logger.debug(f"(General Property Details) Use Teton Idaho = {use_teton_idaho}")
    
    if use_greenwood:
        try:
            logger.debug("(General Property Details) Attempting to import Greenwood scraper...")
            from overrides.property_details.greenwood_details_scrape import GreenwoodPropertyDetailsScraper
            logger.debug("(General Property Details) Greenwood scraper imported successfully")
            scraper = GreenwoodPropertyDetailsScraper(url, config)
            logger.info("(General Property Details) Using Greenwood scraper")
            return scraper.scrape()
        except ImportError as e:
            logger.warning(f"(General Property Details) Greenwood scraper not found, falling back to general scraper. Error: {e}")
            scraper = GeneralPropertyDetailsScraper(url, config)
            return scraper.scrape()
    elif use_teton_idaho:
        try:
            logger.debug("(General Property Details) Attempting to import Teton Idaho scraper...")
            from overrides.property_details.teton_county_id_details import scrape_property_details as teton_idaho_scrape_property_details
            logger.debug("(General Property Details) Teton Idaho scraper imported successfully")
            logger.info("(General Property Details) Using Teton Idaho scraper")
            return teton_idaho_scrape_property_details(url)
        except ImportError as e:
            logger.warning(f"(General Property Details) Teton Idaho scraper not found, falling back to general scraper. Error: {e}")
            scraper = GeneralPropertyDetailsScraper(url, config)
            return scraper.scrape()
    elif use_lincoln:
        try:
            logger.debug("(General Property Details) Attempting to import Lincoln scraper...")
            from overrides.property_details.lincoln_county_wy_details import LincolnPropertyDetailsScraper
            logger.debug("(General Property Details) Lincoln scraper imported successfully")
            scraper = LincolnPropertyDetailsScraper(url, config)
            logger.info("(General Property Details) Using Lincoln scraper")
            return scraper.scrape()
        except ImportError as e:
            logger.warning(f"(General Property Details) Lincoln scraper not found, falling back to general scraper. Error: {e}")
            scraper = GeneralPropertyDetailsScraper(url, config)
            return scraper.scrape()
    elif use_teton:
        try:
            logger.debug("(General Property Details) Attempting to import Teton scraper...")
            from overrides.property_details.teton_county_wy_detials import scrape_property_details as teton_scrape_property_details
            logger.debug("(General Property Details) Teton scraper imported successfully")
            logger.info("(General Property Details) Using Teton scraper")
            return teton_scrape_property_details(url)
        except ImportError as e:
            logger.warning(f"(General Property Details) Teton scraper not found, falling back to general scraper. Error: {e}")
            scraper = GeneralPropertyDetailsScraper(url, config)
            return scraper.scrape()
    else:
        # Use the general scraper for other counties
        logger.info("(General Property Details) Using general scraper")
        scraper = GeneralPropertyDetailsScraper(url, config)
        return scraper.scrape() 