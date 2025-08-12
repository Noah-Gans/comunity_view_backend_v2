"""Greenwood county-specific property details scraper that overrides the general scraper."""
from general_parsers.property_details import GeneralPropertyDetailsScraper
import re
import json
import copy

class GreenwoodPropertyDetailsScraper(GeneralPropertyDetailsScraper):
    """
    Greenwood county-specific property details scraper.
    Handles the nested table structure and building sections specific to Greenwood county pages.
    """
    def scrape(self):
        print("cat mans")
        """Driver method to fetch and extract property details."""
        self.fetch()
        raw_tables = self.extract_all_tables_and_lists()
        self.write_tables_to_file(raw_tables)
        filled = self.map_to_canonical(raw_tables)
        self.write_filled_json(filled)
        return filled
    
    def clean_text(self, text: str) -> str:
        """Clean text by removing \xa0 characters and extra whitespace."""
        if not text:
            return ""
        # Remove \xa0 (non-breaking space) and normalize whitespace
        cleaned = text.replace('\xa0', ' ').replace('\n', ' ').strip()
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned

    def extract_all_tables_and_lists(self) -> dict:
        """Override to handle Greenwood's specific HTML structure."""
        results = {}
        if not self.soup:
            return results
        
        # Extract span-based content (addresses, owners, etc.)
        span_data = self.extract_span_data()
        
        # Extract tables with Greenwood-specific logic
        tables = self.soup.find_all('table')
        print(f"Found {len(tables)} tables in the HTML")
        table_idx = 0
        
        for table in tables:
            table_idx += 1
            print(f"Processing table {table_idx}")
            rows = []
            
            # Get all rows in this table
            table_rows = table.find_all('tr', recursive=False)
            print(f"  Table {table_idx} has {len(table_rows)} rows")
            
            # Process building data if this looks like a building table
            if self.is_building_table(table_rows):
                rows = self.process_building_table(table_rows)
            else:
                # Process as regular table
                rows = self.process_regular_table(table_rows)
            
            if rows:
                results[f'table_{table_idx}'] = rows
                print(f"  Added table_{table_idx} with {len(rows)} rows")
        
        # Combine all extracted data with spans first
        if span_data:
            results['spans'] = span_data
        
        return results

    def extract_span_data(self) -> dict:
        """Extract span-based content (addresses, owners, etc.)."""
        span_data = {}
        for span in self.soup.find_all('span'):
            text = self.clean_text(span.get_text(' ', strip=True))
            if text and len(text) > 2:
                # Address detection
                if any(word in text.upper() for word in ['ST', 'DR', 'AVE', 'ROAD', 'STREET', 'NORTH', 'SOUTH', 'EAST', 'WEST']):
                    if 'property_address' not in span_data:
                        span_data['property_address'] = text
                # Owner detection
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
        return span_data

    def is_building_table(self, table_rows) -> bool:
        """Check if this table contains building data."""
        for row in table_rows:
            if row.get('class') and 'divider' in row.get('class', []):
                cells = row.find_all(['td', 'th'], recursive=False)
                section_text = ' '.join([self.clean_text(c.get_text(' ', strip=True)) for c in cells])
                if 'residential' in section_text.lower() or 'out building' in section_text.lower():
                    return True
        return False

    def process_building_table(self, table_rows) -> list:
        """Process a table that contains building data."""
        
        developments = []
        development = []
        current_building_section = None
        
        for i, row in enumerate(table_rows):
            cells = row.find_all(['td', 'th'], recursive=False)
            print(f"    Row {i} has {len(cells)} cells")
            
            # Handle section dividers (building headers)
            if row.get('class') and 'divider' in row.get('class', []):
                # If we have a current development, save it before starting a new one
                if development:
                    print(f"      Closing development: {development}")
                    developments.append(development)
                
                # Start new development
                current_building_section = [self.clean_text(c.get_text(' ', strip=True)) for c in cells]
                print(f"      Section divider: {current_building_section}")
                development = []
                development.append(current_building_section)
                continue
            
            # Handle This is the main building data row
            if (i == 0 and len(cells) > 2) or (row.get('class') and 'toprow' in row.get('class', [])) or any(cell.name == 'th' for cell in cells):
                main_building_row = [self.clean_text(c.get_text(' ', strip=True)) for c in cells]
                print(f"      Headers: {main_building_row}")
                development.append(main_building_row)
                continue
        
            # Process component rows
            elif len(cells) > 2:
                component_row = [self.clean_text(c.get_text(' ', strip=True)) for c in cells]
                print(f"      Component row: {component_row}")
                if component_row:
                    print(f"      Building component: {component_row}")
                    development.append(component_row)
                    continue

        # Add the final development if it exists
        if development:
            print(f"      Final development: {development}")
            developments.append(development)
        
        print(f"    Developments: {developments}")
        return developments

    def process_regular_table(self, table_rows) -> list:
        """Process a regular table (non-building data)."""
        rows = []
        headers = []
        
        for i, row in enumerate(table_rows):
            cells = row.find_all(['td', 'th'], recursive=False)
            print(f"    Row {i} has {len(cells)} cells")
            
            # Header row
            if (i == 0 and len(cells) > 2) or (row.get('class') and 'toprow' in row.get('class', [])) or any(cell.name == 'th' for cell in cells):
                headers = [self.clean_text(c.get_text(' ', strip=True)) for c in cells]
                print(f"      Headers: {headers}")
                continue
            print(f"      Headers: {headers}")
            print(f"      Cells: {cells}")
            # Data row with headers
            
            # Key-value row
            if len(cells) == 2:
                key = self.clean_text(cells[0].get_text(' ', strip=True))
                value = self.clean_text(cells[1].get_text(' ', strip=True))
                rows.append({key: value})
                print(f"      Key-value row: {key} = {value}")
            # Single cell row
            elif len(cells) == 1:
                value = self.clean_text(cells[0].get_text(' ', strip=True))
                rows.append({'note': value})
                print(f"      Note row: {value}")
            # Multi-column row
            elif len(cells) > 2:
                values = [self.clean_text(c.get_text(' ', strip=True)) for c in cells]

                rows.append({values[-1]: values[0]})
                print(f"      Multi-column row: {values}")
        
        return rows
    
    def map_to_canonical(self, raw_tables: dict) -> dict:
        """Override to handle Greenwood's specific data structure."""
        # Load canonical structure
        with open('property_info_api/structure.json') as f:
            canonical = json.load(f)
        result = copy.deepcopy(canonical)
        developments = []
        
        # Process all data sources
        for source_name, source_data in raw_tables.items():
            print(f"\nProcessing {source_name}:")
            print(f"    ", source_data)
            print(f"    source data 0", source_name[0])
            
            if source_name.startswith('table_'):
                # Check if this is building data (3D array structure)
                if isinstance(source_data, list) and len(source_data) > 0 and isinstance(source_data[0], list):
                    print(f"  Processing building data (3D array): {len(source_data)} developments")
                    
                    for development_idx, development in enumerate(source_data):
                        print(f"    Development {development_idx}: {len(development)} rows")
                        
                        development_name = "Unknown Development"
                        main_building_data = None
                        component_details = []
                        
                        for row_idx, row in enumerate(development):
                            print(f"      Row {row_idx}: {row}")
                            
                            if row_idx == 0:
                                # This is the section divider (development name)
                                development_name = row[0] if row else "Unknown Development"
                                print(f"        -> Development name: {development_name}")
                            elif row_idx == 1:
                                # This is the main building data row
                                if len(row) >= 7:  # Should have all the building attributes
                                    main_building_data = {
                                        'Type': row[0] if len(row) > 0 else '',
                                        'Stories': row[1] if len(row) > 1 else '',
                                        'Sq Ft': row[2] if len(row) > 2 else '',
                                        'Exterior': row[3] if len(row) > 3 else '',
                                        'Roof Cover': row[4] if len(row) > 4 else '',
                                        'Year Built*': row[5] if len(row) > 5 else '',
                                        'Sketch(s)': row[6] if len(row) > 6 else ''
                                    }
                                    
                                    # Also add to 2D array for compatibility
                                    building_row = {
                                        'Building Name': development_name,
                                        'Type': main_building_data['Type'],
                                        'Stories': main_building_data['Stories'],
                                        'Sq Ft': main_building_data['Sq Ft'],
                                        'Exterior': main_building_data['Exterior'],
                                        'Roof Cover': main_building_data['Roof Cover'],
                                        'Year Built*': main_building_data['Year Built*'],
                                        'Sketch(s)': main_building_data['Sketch(s)'],
                                        'Component Type': 'Main Building'  # Main building
                                    }
                                    developments.append(building_row)
                                    print(f"        -> Main building data: {main_building_data}")
                            else:
                                # This is a component row
                                if len(row) >= 1:  # Should have at least description
                                    component_detail = {
                                        'description': row[0] if len(row) > 0 else '',
                                        'Stories': '',
                                        'Sq Ft': row[1] if len(row) > 1 else '',
                                        'Exterior': row[2] if len(row) > 2 else '',
                                        'Roof Cover': row[3] if len(row) > 3 else '',
                                        'Year Built*': row[4] if len(row) > 4 else '',
                                        'Sketch(s)': row[5] if len(row) > 5 else ''
                                    }
                                    component_details.append(component_detail)
                                    
                                    # Also add to 2D array for compatibility
                                    component_row = {
                                        'Building Name': development_name,
                                        'Building Component': component_detail['description'],
                                        'Stories': component_detail['Stories'],
                                        'Sq Ft': component_detail['Sq Ft'],
                                        'Exterior': component_detail['Exterior'],
                                        'Roof Cover': component_detail['Roof Cover'],
                                        'Year Built*': component_detail['Year Built*'],
                                        'Sketch(s)': component_detail['Sketch(s)'],
                                        'Component Type': 'Component'
                                    }
                                    developments.append(component_row)
                                    print(f"        -> Component detail: {component_detail}")
                        
                        
                else:
                    # Process regular table data
                    for row in source_data:
                        
                        
                        # Skip rows with 'note' entries
                        if isinstance(row, dict) and 'note' in row:
                            print("    Skipping row with 'note'")
                            continue
                        
                                                # Handle parcel/land data
                        if isinstance(row, dict) and 'Building Section' not in row:
                            # First pass: try with key as the field name
                            matched = False
                            for k, v in row.items():
                                norm_k = self.normalize_key(k)
                                print(f"    [TOP PASS 1] Key: {k} (norm: {norm_k}), Value: {v}")
                                
                                for i in range(2):
                                    
                                    if i == 1:
                                        print(f"    [TOP PASS 2] Key: {k} (norm: {norm_k}), Value: {v}")
                                        norm_k = self.normalize_key(v)
                                        v = k
                                    print(f"    'residential' in norm_k", 'residential' in norm_k)
                                            
                                    # Map top-level fields
                                    if re.search(r'pidn', norm_k):
                                        result['county_parcel_id'] = v
                                        print(f"      -> Matched to county_parcel_id")
                                        matched = True
                                    elif re.search(r'tax id', norm_k):
                                        result['tax_id'] = v
                                        print(f"      -> Matched to tax_id")
                                        matched = True
                                    elif re.search(r'street address', norm_k):
                                        result['physical_address'] = v
                                        print(f"      -> Matched to physical_address")
                                        matched = True
                                    elif re.search(r'mailing address', norm_k):
                                        result['mailing_address'] = v
                                        print(f"      -> Matched to mailing_address")
                                        matched = True
                                    elif re.search(r'owner', norm_k):
                                        result['owner_name'] = v
                                        print(f"      -> Matched to owner_name")
                                        matched = True
                                    elif re.search(r'tax district', norm_k):
                                        result['tax_district'] = v
                                        print(f"      -> Matched to tax_district")
                                        matched = True
                                    elif re.search(r'acres', norm_k):
                                        result['total_acres'] = v
                                        print(f"      -> Matched to total_acres")
                                        matched = True
                                    elif re.search(r'location', norm_k):
                                        result['legal']['location'] = v
                                        print(f"      -> Matched to legal.location")
                                        matched = True
                                    elif re.search(r'deed', norm_k):
                                        result['deed'] = v
                                        print(f"      -> Matched to deed")
                                        matched = True
                                    elif re.search(r'actual value', norm_k):
                                        print(f"      -> Matched to value_summary", v)
                                        
                                        # Extract total actual value (first dollar amount)
                                        total_match = re.search(r'\$\s*([0-9,]+)', v)
                                        if total_match:
                                            result['value_summary']['total_value'] = f"${total_match.group(1)}"
                                            print(f"      -> Extracted total actual value: ${total_match.group(1)}")
                                        
                                        # Extract land and improvement values from the value string
                                        land_match = re.search(r'\$\s*([0-9,]+)\s+Land', v)
                                        improvement_match = re.search(r'\$\s*([0-9,]+)\s+Improvements', v)
                                        if land_match:
                                            result['value_summary']['land'] = f"${land_match.group(1)}"
                                            print(f"      -> Extracted land value: ${land_match.group(1)}")
                                        if improvement_match:
                                            result['value_summary']['developments'] = f"${improvement_match.group(1)}"
                                            print(f"      -> Extracted improvement value: ${improvement_match.group(1)}")
                                        matched = True

                                    elif 'total' in norm_k:
                                            result['total_acres'] = v
                                            print(f"      -> Matched total_acres with value as identifier: {k}")
                                            matched = True
                                    elif 'residential' in norm_k:
                                        print(f"      -> Matched residential acreage: {k} acres")
                                        result['acreage_breakdown']['residential'] = v
                                        matched = True
                                    elif 'agricultural' in norm_k:
                                        result['acreage_breakdown']['agricultural'] = v
                                        print(f"      -> Matched agricultural acreage: {k} acres")
                                        matched = True
                                    elif 'commercial' in norm_k:
                                        result['acreage_breakdown']['commercial'] = v
                                        print(f"      -> Matched commercial acreage: {k} acres")
                                        matched = True
                                    elif 'industrial' in norm_k:
                                        result['acreage_breakdown']['industrial'] = v
                                        print(f"      -> Matched industrial acreage: {k} acres")
                                        matched = True
                                    elif 'other' in norm_k or 'misc' in norm_k or 'mixed' in norm_k:
                                        result['acreage_breakdown']['other'] = v
                                        print(f"      -> Matched other acreage: {k} acres")
                                        matched = True
                                    # Second pass: if no matches found, try with value as the field name
                                    if matched:
                                        print(f"      -> Cam HERE")
                                        break
                                    
                        else:
                            print(f"      -> Matched to building_data_2d", row)
                            
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
                        print(f"      -> Found percent_ownership: {v}")
        
        # Add the 2D building data to the result
        
        # Add developments to the canonical structure
        result['developments'] = developments
        
        return result

def scrape_property_details(url: str, config: dict = None) -> dict:
    """Instantiate and use the Greenwood-specific PropertyDetailsScraper."""
    scraper = GreenwoodPropertyDetailsScraper(url, config)
    return scraper.scrape()
