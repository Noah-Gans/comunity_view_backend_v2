"""Property details scraper with domain-based routing, extensible class, and robust helpers."""
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
import json
import copy

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
        filename = f'property_details_{self.county}_{self.timestamp}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

    def write_tables_to_file(self, tables: dict):
        """Write the extracted tables to a JSON file named by county and timestamp."""
        filename = f'property_details_tables_{self.county}_{self.timestamp}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tables, f, indent=2, ensure_ascii=False)

    def write_filled_json(self, filled: dict):
        """Write the filled canonical structure to a JSON file named by county and timestamp."""
        filename = f'property_details_filled_{self.county}_{self.timestamp}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(filled, f, indent=2, ensure_ascii=False)

    def fetch(self):
        """Fetch the page and parse with BeautifulSoup. Writes raw HTML to a file for debugging."""
        resp = requests.get(self.url, timeout=10)
        resp.raise_for_status()
        self.write_html_to_file(resp.text)
        self.soup = BeautifulSoup(resp.text, 'html.parser')

    def extract_all_tables_and_lists(self) -> dict:
        """Extracts all tables and definition lists as thoroughly as possible, including nested tables, without mixing parent and child rows."""
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
        print(f"Found {len(tables)} tables in the HTML")
        table_idx = 0
        for table in tables:
            table_idx += 1
            print(f"Processing table {table_idx}")
            rows = []
            headers = []
            
            # Get all rows in this table
            table_rows = table.find_all('tr', recursive=False)
            print(f"  Table {table_idx} has {len(table_rows)} rows")
            
            for i, row in enumerate(table_rows):
                cells = row.find_all(['td', 'th'], recursive=False)
                print(f"    Row {i} has {len(cells)} cells")
                
                # Header row: more than 2 cells, or first row, or has th elements
                if (i == 0 and len(cells) > 2) or (row.get('class') and 'toprow' in row.get('class', [])) or any(cell.name == 'th' for cell in cells):
                    headers = [c.get_text(' ', strip=True) for c in cells]
                    print(f"      Headers: {headers}")
                    continue
                
                # Data row with headers
                if headers and len(cells) == len(headers):
                    row_data = {h: c.get_text(' ', strip=True) for h, c in zip(headers, cells)}
                    rows.append(row_data)
                    print(f"      Data row: {row_data}")
                # Key-value row
                elif len(cells) == 2:
                    key = cells[0].get_text(' ', strip=True)
                    value = cells[1].get_text(' ', strip=True)
                    rows.append({key: value})
                    print(f"      Key-value row: {key} = {value}")
                # Feature/note row
                elif len(cells) == 1:
                    value = cells[0].get_text(' ', strip=True)
                    rows.append({'note': value})
                    print(f"      Note row: {value}")
                # Multi-column row without headers
                elif len(cells) > 2:
                    # Create a simple list of values
                    values = [c.get_text(' ', strip=True) for c in cells]
                    rows.append({'values': values})
                    print(f"      Multi-column row: {values}")
            
            if rows:
                results[f'table_{table_idx}'] = rows
                print(f"  Added table_{table_idx} with {len(rows)} rows")
        
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
        
        return results

    def normalize_key(self, k):
        # Remove non-breaking spaces, colons, extra whitespace, make lowercase
        k = re.sub(r'[\xa0\s]+', ' ', k)
        k = k.replace(':', '').strip().lower()
        return k

    def map_to_canonical(self, raw_tables: dict) -> dict:
        """
        Maps raw table data to a canonical JSON structure defined in structure.json.
        This function fills in the values from the raw tables into the canonical structure.
        """
        # Define robust matching options for each canonical field
        field_patterns = {
            'county_parcel_id': [r'pidn', r'parcel number'],
            'tax_id': [r'tax id'],
            'physical_address': [r'street address', r'property address', r'address'],
            'mailing_address': [r'mailing address'],
            'owner_name': [r'owner'],
            'tax_district': [r'tax district'],
            'total_acres': [r'total acres', r'acres'],
            'legal.subdivision': [r'subdivision'],
            'legal.lot': [r'lot'],
            'legal.block': [r'block'],
            'legal.section': [r'section'],
            'legal.township': [r'township'],
            'legal.range': [r'range'],
            'legal.extended': [r'extended legal', r'extended'],
            'value_summary.land': [r'land'],
            'value_summary.developments': [r'improvement', r'developments'],
        }
        # Load canonical structure
        with open('property_info_api/structure.json') as f:
            canonical = json.load(f)
        result = copy.deepcopy(canonical)
        developments = []
        in_development_section = False
        current_dev = None
        
        # Process all data sources (tables, dl, spans, divs, etc.)
        for source_name, source_data in raw_tables.items():
            print(f"\nProcessing {source_name}:")
            
            # Handle different data source types
            if source_name.startswith('table_') or source_name.startswith('dl_'):
                # Process table/dl data as before
                for row in source_data:
                    print(f"  Row: {row}")
                    matched = False
                    
                    # NEW: Handle value information tables
                    if isinstance(row, dict) and 'Value Type' in row:
                        print(f"    [VALUE] Found value table row: {row}")
                        value_type = row.get('Value Type', '')
                        appraised_value = row.get('Appraised Value', '')
                        if value_type and appraised_value:
                            if 'land' in value_type.lower():
                                result['value_summary']['land'] = appraised_value
                                print(f"      -> Matched land value: {appraised_value}")
                                matched = True
                            elif 'improvement' in value_type.lower():
                                result['value_summary']['developments'] = appraised_value
                                print(f"      -> Matched improvement value: {appraised_value}")
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
                        print("    -> Detected start of development section")
                    if in_development_section and current_dev:
                        # Fill development fields
                        for k, v in row.items():
                            norm_k = self.normalize_key(k)
                            print(f"    [DEV] Key: {k} (norm: {norm_k}), Value: {v}")
                            if re.search(r'building id|building_id', norm_k):
                                current_dev['building_id'] = v
                                print(f"      -> Matched to development building_id")
                            if re.search(r'residential|type|out building|development', norm_k):
                                current_dev['type'] = v
                                print(f"      -> Matched to development type")
                            if re.search(r'year built', norm_k):
                                current_dev['attributes']['year_built'] = v
                                print(f"      -> Matched to development year_built")
                            if re.search(r'sq ft', norm_k):
                                current_dev['attributes']['sq_ft'] = v
                                print(f"      -> Matched to development sq_ft")
                            if re.search(r'bedroom', norm_k):
                                current_dev['attributes']['bedrooms'] = v
                                print(f"      -> Matched to development bedrooms")
                            if re.search(r'bath', norm_k):
                                current_dev['attributes']['baths'] = v
                                print(f"      -> Matched to development baths")
                    else:
                        # Fill top-level fields
                        for k, v in row.items():
                            norm_k = self.normalize_key(k)
                            print(f"    [TOP] Key: {k} (norm: {norm_k}), Value: {v}")
                            for field, patterns in field_patterns.items():
                                for pat in patterns:
                                    if re.search(pat, norm_k):
                                        # Support nested fields
                                        if '.' in field:
                                            parent, child = field.split('.')
                                            result[parent][child] = v
                                        else:
                                            result[field] = v
                                        print(f"      -> Matched to {field} (pattern: {pat})")
                                        matched = True
                                        break
                                if matched:
                                    break
                        if not matched:
                            print(f"      -> No match for this row.")
            
            elif source_name == 'spans':
                # Process span data
                print(f"  Processing spans: {source_data}")
                for k, v in source_data.items():
                    print(f"    [SPAN] Key: {k}, Value: {v}")
                    if k == 'property_address':
                        result['physical_address'] = v
                        print(f"      -> Matched to physical_address")
                    elif k == 'owner_name':
                        result['owner_name'] = v
                        print(f"      -> Matched to owner_name")
                    elif k == 'percent_ownership':
                        # Store as additional info
                        print(f"      -> Found percent_ownership: {v}")
            
            elif source_name == 'divs':
                # Process div data
                print(f"  Processing divs: {source_data}")
                for k, v in source_data.items():
                    print(f"    [DIV] Key: {k}, Value: {v}")
                    # Try to extract addresses from div content
                    if 'address' in k.lower():
                        # Look for address patterns in the text
                        address_match = re.search(r'(\d+\s+[A-Z\s]+(?:ST|DR|AVE|ROAD|STREET))', v, re.IGNORECASE)
                        if address_match and not result['physical_address']:
                            result['physical_address'] = address_match.group(1).strip()
                            print(f"      -> Extracted physical_address from div")
                    elif 'owner' in k.lower():
                        # Look for owner patterns in the text
                        owner_match = re.search(r'([A-Z\s&]+(?:TRUSTEE|TRUST|LLC|INC))', v, re.IGNORECASE)
                        if owner_match and not result['owner_name']:
                            result['owner_name'] = owner_match.group(1).strip()
                            print(f"      -> Extracted owner_name from div")
            
            elif source_name == 'strong_tags':
                # Process strong tag data
                print(f"  Processing strong tags: {source_data}")
                for k, v in source_data.items():
                    print(f"    [STRONG] Key: {k}, Value: {v}")
                    norm_k = self.normalize_key(k)
                    for field, patterns in field_patterns.items():
                        for pat in patterns:
                            if re.search(pat, norm_k):
                                if '.' in field:
                                    parent, child = field.split('.')
                                    result[parent][child] = v
                                else:
                                    result[field] = v
                                print(f"      -> Matched to {field} (pattern: {pat})")
                                break
            
            elif source_name == 'p_tags':
                # Process p tag data
                print(f"  Processing p tags: {source_data}")
                for k, v in source_data.items():
                    print(f"    [P] Key: {k}, Value: {v}")
                    if 'extended_legal' in k.lower():
                        result['legal']['extended'] = v
                        print(f"      -> Matched to legal.extended")
        
        if current_dev:
            developments.append(current_dev)
        # Remove empty developments
        result['developments'] = [d for d in developments if any(v for v in d['attributes'].values())]
        return result

    def scrape(self) -> dict:
        """Driver method to fetch and extract property details."""
        self.fetch()
        raw_tables = self.extract_all_tables_and_lists()
        self.write_tables_to_file(raw_tables)
        filled = self.map_to_canonical(raw_tables)
        self.write_filled_json(filled)
        return filled

def scrape_property_details(url: str, config: dict = None) -> dict:
    """Instantiate and use the appropriate PropertyDetailsScraper based on the URL and county."""
    # Get county from config if available
    county = None
    if config and 'county' in config:
        county = config['county'].lower()
    
    print(f"DEBUG: URL = {url}")
    print(f"DEBUG: County = {county}")
    
    # Check if this is a Greenwood county URL or if county is Fremont/Sublette
    use_greenwood = (
        'greenwood' in url.lower() or 
        'maps.greenwoodmap.com' in url.lower() or
        county in ['fremont', 'sublette']
    )
    use_lincoln = (
        'lincoln' in url.lower() or
        county in ['lincoln']
    )
    use_teton_idaho = (
        'tetonidaho' in url.lower() or
        'tetonidaho.maps.arcgis.com' in url.lower() or
        county in ['teton_idaho', 'teton idaho', 'tetonidaho']
    )
    use_teton = (
        ('teton' in url.lower() and 'tetonidaho' not in url.lower()) or
        'tetoncountywy.gov' in url.lower() or
        county in ['teton']
    )
    
    print(f"DEBUG: Use Greenwood = {use_greenwood}")
    print(f"DEBUG: 'greenwood' in url = {'greenwood' in url.lower()}")
    print(f"DEBUG: 'maps.greenwoodmap.com' in url = {'maps.greenwoodmap.com' in url.lower()}")
    print(f"DEBUG: county in ['fremont', 'sublette'] = {county in ['fremont', 'sublette']}")
    print(f"DEBUG: Use Lincoln = {use_lincoln}")
    print(f"DEBUG: 'lincoln' in url = {'lincoln' in url.lower()}")
    print(f"DEBUG: county in ['lincoln'] = {county in ['lincoln']}")
    print(f"DEBUG: Use Teton = {use_teton}")
    print(f"DEBUG: 'teton' in url = {'teton' in url.lower()}")
    print(f"DEBUG: 'tetoncountywy.gov' in url = {'tetoncountywy.gov' in url.lower()}")
    print(f"DEBUG: county in ['teton'] = {county in ['teton']}")
    print(f"DEBUG: Use Teton Idaho = {use_teton_idaho}")
    print(f"DEBUG: 'tetonidaho' in url = {'tetonidaho' in url.lower()}")
    print(f"DEBUG: 'tetonidaho.maps.arcgis.com' in url = {'tetonidaho.maps.arcgis.com' in url.lower()}")
    print(f"DEBUG: county in ['teton_idaho', 'teton idaho'] = {county in ['teton_idaho', 'teton idaho']}")
    if use_greenwood:
        try:
            print("DEBUG: Attempting to import Greenwood scraper...")
            from overrides.greenwood_details_scrape import GreenwoodPropertyDetailsScraper
            print("DEBUG: Greenwood scraper imported successfully")
            scraper = GreenwoodPropertyDetailsScraper(url, config)
            print("DEBUG: Using Greenwood scraper")
            return scraper.scrape()
        except ImportError as e:
            print(f"Warning: Greenwood scraper not found, falling back to general scraper. Error: {e}")
            scraper = GeneralPropertyDetailsScraper(url, config)
            return scraper.scrape()
    elif use_teton_idaho:
        try:
            print("DEBUG: Attempting to import Teton Idaho scraper...")
            from overrides.teton_county_id_details import scrape_property_details as teton_idaho_scrape_property_details
            print("DEBUG: Teton Idaho scraper imported successfully")
            print("DEBUG: Using Teton Idaho scraper")
            return teton_idaho_scrape_property_details(url)
        except ImportError as e:
            print(f"Warning: Teton Idaho scraper not found, falling back to general scraper. Error: {e}")
            scraper = GeneralPropertyDetailsScraper(url, config)
            return scraper.scrape()
    elif use_lincoln:
        try:
            print("DEBUG: Attempting to import Lincoln scraper...")
            from overrides.lincoln_county_details import LincolnPropertyDetailsScraper
            print("DEBUG: Lincoln scraper imported successfully")
            scraper = LincolnPropertyDetailsScraper(url, config)
            print("DEBUG: Using Lincoln scraper")
            return scraper.scrape()
        except ImportError as e:
            print(f"Warning: Lincoln scraper not found, falling back to general scraper. Error: {e}")
            scraper = GeneralPropertyDetailsScraper(url, config)
            return scraper.scrape()
    elif use_teton:
        try:
            print("DEBUG: Attempting to import Teton scraper...")
            from overrides.teton_county_wy_detials import scrape_property_details as teton_scrape_property_details
            print("DEBUG: Teton scraper imported successfully")
            print("DEBUG: Using Teton scraper")
            return teton_scrape_property_details(url)
        except ImportError as e:
            print(f"Warning: Teton scraper not found, falling back to general scraper. Error: {e}")
            scraper = GeneralPropertyDetailsScraper(url, config)
            return scraper.scrape()
    else:
        # Use the general scraper for other counties
        print("DEBUG: Using general scraper")
        scraper = GeneralPropertyDetailsScraper(url, config)
        return scraper.scrape() 