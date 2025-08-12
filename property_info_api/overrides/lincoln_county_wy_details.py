"""Lincoln county-specific property details scraper that overrides the general scraper."""
from general_parsers.property_details import GeneralPropertyDetailsScraper
import re
import json
import copy

class LincolnPropertyDetailsScraper(GeneralPropertyDetailsScraper):
    """
    Lincoln county-specific property details scraper.
    Handles the specific HTML structure and table formats for Lincoln county pages.
    """
    
    def scrape(self) -> dict:
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
        """Override to handle Lincoln's specific HTML structure."""
        results = {}
        if not self.soup:
            return results
        # Extract span-based content (addresses, owners, etc.)
        span_data = self.extract_span_data()
        # Extract Lincoln's div-based property information
        div_data = self.extract_div_based_data()
        # Extract definition lists (dl/dt/dd)
        dl_data = self.extract_definition_lists()
        # Extract building/development data from divs
        building_data = self.extract_building_data()
        
        # Extract tables with Lincoln-specific logic
        tables = self.soup.find_all('table')
        print(f"Found {len(tables)} tables in the HTML")
        table = tables[0]
        rows = []
        # Debug: Check different ways to find rows
        all_trs = table.find_all('tr')
        direct_trs = table.find_all('tr', recursive=False)
        tbody_trs = []
        tbody = table.find('tbody')
        if tbody:
            tbody_trs = tbody.find_all('tr', recursive=False)
        if direct_trs:
            table_rows = direct_trs
        elif tbody_trs:
            table_rows = tbody_trs
        else:
            table_rows = all_trs
        print(f"  Using {len(table_rows)} rows for processing")
        rows = self.process_regular_table(table_rows)
        
        if rows:
            print(f"    rows: {len(rows)}")
            results['table_1'] = rows
        
        # Combine all extracted data
        if span_data:
            results['spans'] = span_data
        if div_data:
            results['divs'] = div_data
        if dl_data:
            results['definition_lists'] = dl_data
        if building_data:
            results['buildings'] = building_data
        
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

    def extract_div_based_data(self) -> dict:
        """Extract data from Lincoln's div-based structure."""
        div_data = {}
        
        # Find the General Information section
        general_info = self.soup.find('div', class_='ibox-content')
        if general_info:
            print("Found General Information section")
            
            # Extract Property Address
            property_address_section = general_info.find('h5', string='Property Address')
            if property_address_section:
                address_div = property_address_section.find_next('span')
                if address_div:
                    address = self.clean_text(address_div.get_text())
                    div_data['Property Address'] = address
                    print(f"  Property Address: {address}")
            
            # Extract Owner Information
            owner_section = general_info.find('h5', string='Owner Name & Address')
            if owner_section:
                owner_div = owner_section.find_next_sibling('hr').find_next_sibling()
                owner_spans = []
                current = owner_div
                while current and current.name != 'h5':
                    if current.name == 'span':
                        text = self.clean_text(current.get_text())
                        if text and text != 'Primary Owner':
                            owner_spans.append(text)
                    current = current.find_next_sibling()
                
                if owner_spans:
                    # First span is usually the owner name
                    div_data['Primary Owner'] = owner_spans[0]
                    print(f"  Primary Owner: {owner_spans[0]}")
                    
                    # Combine address parts
                    if len(owner_spans) > 1:
                        mailing_address = ' '.join(owner_spans[1:])
                        div_data['Mailing Address'] = mailing_address
                        print(f"  Mailing Address: {mailing_address}")
            
            # Extract Extended Legal
            extended_legal = general_info.find('strong', string='Extended Legal:')
            if extended_legal:
                legal_text = self.clean_text(extended_legal.next_sibling)
                div_data['Extended Legal'] = legal_text
                print(f"  Extended Legal: {legal_text}")
        
        return div_data

    def extract_definition_lists(self) -> dict:
        """Extract data from dl/dt/dd definition lists."""
        dl_data = {}
        
        # Find all definition lists
        dls = self.soup.find_all('dl')
        print(f"Found {len(dls)} definition lists")
        
        for dl in dls:
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            
            # Match dt with dd
            for dt, dd in zip(dts, dds):
                key = self.clean_text(dt.get_text())
                value = self.clean_text(dd.get_text())
                if key and value:
                    dl_data[key] = value
                    print(f"  {key}: {value}")
        
        return dl_data

    def extract_building_data(self) -> list:
        """Extract building/development data from Lincoln's HTML structure."""
        buildings = []
        
        # Look for building sections - they typically have h4 headers like "Building ID 1"
        building_sections = self.soup.find_all('h4')
        
        for section in building_sections:
            section_text = self.clean_text(section.get_text())
            if 'building id' in section_text.lower():
                print(f"Found building section: {section_text}")
                
                # Extract building ID
                building_id_match = re.search(r'building id\s*(\d+)', section_text.lower())
                building_id = building_id_match.group(1) if building_id_match else "Unknown"
                
                building_data = {
                    'Building Name': f"Building {building_id}",
                    'Building ID': building_id,
                    'Type': '',
                    'Built As': '',
                    'Property Type': '',
                    'Occupancy': '',
                    'Stories': '',
                    'Total Sq Ft': '',
                    'Sq Ft': '',
                    'Condo Sq Ft': '',
                    'Bsmt Sq Ft': '',
                    'Bsmt Fin Sq Ft': '',
                    'Exterior': '',
                    'Class Descr': '',
                    'Interior': '',
                    'Roof Type': '',
                    'Roof Cover': '',
                    'Foundation': '',
                    'Year Built': '',
                    'Year Built*': '',
                    'Year Remodel': '',
                    'Heat': '',
                    'Rooms': '',
                    'Bed Rooms': '',
                    'Bedrooms': '',
                    'Baths': '',
                    'Units': '',
                    'Unit Type': '',
                    'Quality': '',
                    'Condition': '',
                    'Sketch(s)': '',
                    'Component Type': 'Main Building'
                }
                
                # Find the ibox-content div that contains the building details
                # The h4 is inside ibox-heading, so we need to go up to the parent ibox and find ibox-content
                ibox_heading = section.find_parent('div', class_='ibox-heading')
                if ibox_heading:
                    ibox_content = ibox_heading.find_next_sibling('div', class_='ibox-content')
                else:
                    # Fallback: try to find ibox-content as direct sibling of h4
                    ibox_content = section.find_next_sibling('div', class_='ibox-content')
                if ibox_content:
                    print(f"  Found ibox-content for {section_text}")
                    
                    # Look for all definition lists in this building section
                    dls = ibox_content.find_all('dl')
                    print(f"  Found {len(dls)} definition lists")
                    
                    for dl_idx, dl in enumerate(dls):
                        print(f"    Processing dl {dl_idx}")
                        dts = dl.find_all('dt')
                        dds = dl.find_all('dd')
                        print(f"      Found {len(dts)} dt elements and {len(dds)} dd elements")
                        
                        for dt, dd in zip(dts, dds):
                            key = self.clean_text(dt.get_text()).lower()
                            value = self.clean_text(dd.get_text())
                            
                            print(f"      Processing: '{key}' = '{value}'")
                            
                            if key and value:
                                # Map building attributes - store in exact key match first, then populate Type
                                if 'heat' in key:
                                    building_data['Heat'] = value
                                    print(f"        -> Heat: {value}")
                                elif 'total sq ft' in key:
                                    building_data['Total Sq Ft'] = value
                                    building_data['Sq Ft'] = value  # Also populate generic Sq Ft
                                    print(f"        -> Total Sq Ft: {value}")
                                elif 'condo sq ft' in key:
                                    building_data['Condo Sq Ft'] = value
                                    print(f"        -> Condo Sq Ft: {value}")
                                elif 'bsmt sq ft' in key and 'fin' not in key:
                                    building_data['Bsmt Sq Ft'] = value
                                    print(f"        -> Bsmt Sq Ft: {value}")
                                elif 'bsmt fin sq ft' in key:
                                    building_data['Bsmt Fin Sq Ft'] = value
                                    print(f"        -> Bsmt Fin Sq Ft: {value}")
                                elif 'property type' in key:
                                    building_data['Property Type'] = value
                                    building_data['Type'] = value  # Also populate generic Type
                                    print(f"        -> Property Type: {value}")
                                elif 'built as' in key:
                                    building_data['Built As'] = value
                                    if not building_data['Type']:  # Don't override property type
                                        building_data['Type'] = value
                                    print(f"        -> Built As: {value}")
                                elif 'occupancy' in key:
                                    building_data['Occupancy'] = value
                                    if not building_data['Type']:
                                        building_data['Type'] = value
                                        print(f"        -> Type (from occupancy): {value}")
                                elif 'roof type' in key:
                                    building_data['Roof Type'] = value
                                    building_data['Roof Cover'] = value  # Also populate generic
                                    print(f"        -> Roof Type: {value}")
                                elif 'roof cover' in key:
                                    building_data['Roof Cover'] = value
                                    print(f"        -> Roof Cover: {value}")
                                elif 'foundation' in key:
                                    building_data['Foundation'] = value
                                    print(f"        -> Foundation: {value}")
                                elif 'year built' in key and 'remodel' not in key:
                                    building_data['Year Built'] = value
                                    building_data['Year Built*'] = value  # Also populate generic
                                    print(f"        -> Year Built: {value}")
                                elif 'year remodel' in key:
                                    building_data['Year Remodel'] = value
                                    print(f"        -> Year Remodel: {value}")
                                elif key == 'rooms':
                                    building_data['Rooms'] = value
                                    print(f"        -> Rooms: {value}")
                                elif 'bed rooms' in key:
                                    building_data['Bed Rooms'] = value
                                    building_data['Bedrooms'] = value  # Also populate generic
                                    print(f"        -> Bed Rooms: {value}")
                                elif key == 'bedrooms':
                                    building_data['Bedrooms'] = value
                                    print(f"        -> Bedrooms: {value}")
                                elif 'bath' in key:
                                    building_data['Baths'] = value
                                    print(f"        -> Baths: {value}")
                                elif key == 'units':
                                    building_data['Units'] = value
                                    print(f"        -> Units: {value}")
                                elif 'unit type' in key:
                                    building_data['Unit Type'] = value
                                    print(f"        -> Unit Type: {value}")
                                elif 'quality' in key:
                                    building_data['Quality'] = value
                                    print(f"        -> Quality: {value}")
                                elif 'condition' in key:
                                    building_data['Condition'] = value
                                    print(f"        -> Condition: {value}")
                                elif 'class descr' in key:
                                    building_data['Class Descr'] = value
                                    building_data['Exterior'] = value  # Also populate generic
                                    print(f"        -> Class Descr: {value}")
                                elif key == 'exterior':
                                    building_data['Exterior'] = value
                                    print(f"        -> Exterior: {value}")
                                elif 'interior' in key:
                                    building_data['Interior'] = value
                                    print(f"        -> Interior: {value}")
                                elif 'stories' in key:
                                    building_data['Stories'] = value
                                    print(f"        -> Stories: {value}")
                                else:
                                    print(f"        -> Unmatched: {key} = {value}")
                else:
                    print(f"  No ibox-content found for {section_text}")
                
                # Add the building to our list
                buildings.append(building_data)
                print(f"  Added building: {building_data}")
        
        # If no buildings found with h4 headers, look for alternative structures
        if not buildings:
            print("No h4 building sections found, looking for alternative structures...")
            
            # Look for any divs that might contain building information
            building_divs = self.soup.find_all('div', class_=['ibox', 'building-info', 'property-details'])
            for div in building_divs:
                div_text = self.clean_text(div.get_text()[:200])  # First 200 chars
                if any(keyword in div_text.lower() for keyword in ['building', 'property type', 'sq ft', 'year built']):
                    print(f"Found potential building div: {div_text}")
                    # Extract basic building info from this div
                    # (Add more specific extraction logic here if needed)
        
        return buildings

  
    def process_regular_table(self, table_rows) -> list:
        """Process a regular table (non-building data)."""
        rows = []
        headers = []
        
        # Extract land value (row 0)
        cells_land = table_rows[0].find_all(['td', 'th'], recursive=False)
        values_land = [self.clean_text(c.get_text(' ', strip=True)) for c in cells_land]
        land_value = float(values_land[-3].replace('$', '').replace(',', '').replace('.00', ''))  # Appraised value column
        rows.append({"Land": land_value})
        print(f"  Land value: {land_value}")
        
        # Extract improvement values (rows 1 and 2)
        cells_dev_1 = table_rows[1].find_all(['td', 'th'], recursive=False)
        values_dev_1 = [self.clean_text(c.get_text(' ', strip=True)) for c in cells_dev_1]
        improvement_1 = float(values_dev_1[-3].replace('$', '').replace(',', '').replace('.00', ''))
        
        cells_dev_2 = table_rows[2].find_all(['td', 'th'], recursive=False)
        values_dev_2 = [self.clean_text(c.get_text(' ', strip=True)) for c in cells_dev_2]
        improvement_2 = float(values_dev_2[-3].replace('$', '').replace(',', '').replace('.00', ''))
        
        # Calculate total improvements
        total_improvement = improvement_1 + improvement_2
        rows.append({"Improvement": str(total_improvement)})
        rows.append({"Total": str(land_value + total_improvement)})
        
        return rows
    

    def map_to_canonical(self, raw_tables: dict) -> dict:
        """Override to handle Lincoln's specific data structure."""
        # Load canonical structure
        with open('structure.json') as f:
            canonical = json.load(f)
        result = copy.deepcopy(canonical)
        developments = []
        
        # Process all data sources
        for source_name, source_data in raw_tables.items():
            print(f"\nProcessing {source_name}:")
            print(f"    {source_data}")
            
            if source_name.startswith('table_'):
                # Skip tables that contain 'note' entries
                if isinstance(source_data, list) and any(isinstance(row, dict) and 'note' in row for row in source_data):
                    print(f"  Skipping {source_name} - contains 'note' entries")
                    continue
                
                # Check if this is building data (3D array structure)
                if isinstance(source_data, list) and len(source_data) > 0 and isinstance(source_data[0], list):
                    print(f"  Processing building data (3D array): {len(source_data)} buildings")
                    
                    for building_idx, building in enumerate(source_data):
                        print(f"    Building {building_idx}: {len(building)} rows")
                        
                        building_data = {}
                        building_name = f"Building {building_idx + 1}"
                        
                        for row_idx, row in enumerate(building):
                            print(f"      Row {row_idx}: {row}")
                            
                            if row_idx == 0 and 'building id' in ' '.join(row).lower():
                                # Extract building ID
                                for cell in row:
                                    if cell and cell.lower() != 'building id':
                                        building_name = f"Building {cell}"
                                        break
                                print(f"        -> Building name: {building_name}")
                            
                            elif len(row) == 2:
                                # Key-value pair
                                key = self.clean_text(row[0])
                                value = self.clean_text(row[1])
                                if key and value:
                                    building_data[key] = value
                                    print(f"        -> {key}: {value}")
                        
                        # Create building entry
                        if building_data:
                            building_entry = {
                                'Building Name': building_name,
                                'Type': building_data.get('Built As', building_data.get('Property Type', '')),
                                'Stories': building_data.get('Stories', ''),
                                'Sq Ft': building_data.get('Total Sq Ft', ''),
                                'Exterior': building_data.get('Exterior', building_data.get('Class Descr', '')),
                                'Roof Cover': building_data.get('Roof Cover', building_data.get('Fin Roof Cover', '')),
                                'Year Built*': building_data.get('Year Built', ''),
                                'Sketch(s)': '',
                                'Component Type': 'Main Building'
                            }
                            developments.append(building_entry)
                            print(f"        -> Created building: {building_entry}")
                
                else:
                    # Check if this is a value breakdown table
                    #
                    
                    # Process regular table data
                    for row in source_data:
                        print(f"  Row: {row}")
                        
                        # Skip rows with 'note' entries
                        if isinstance(row, dict) and 'note' in row:
                            print("    Skipping row with 'note'")
                            continue
                        
                        # Handle parcel/land data
                        if isinstance(row, dict):
                            matched = False
                            for k, v in row.items():
                                # Two-pass approach like Greenwood
                                for pass_num in range(2):
                                    norm_k = self.normalize_key(k if pass_num == 0 else v)
                                    value = v if pass_num == 0 else k
                                    
                                    print(f"    [PASS {pass_num + 1}] Key: {k}, Value: {v} (norm: {norm_k})")
                                    
                                    # Map top-level fields
                                    if re.search(r'pidn', norm_k):
                                        result['county_parcel_id'] = value
                                        print(f"      -> Matched to county_parcel_id")
                                        matched = True
                                    elif re.search(r'tax id', norm_k):
                                        result['tax_id'] = value
                                        print(f"      -> Matched to tax_id")
                                        matched = True
                                    elif re.search(r'parcel number', norm_k):
                                        result['county_parcel_id'] = value
                                        print(f"      -> Matched to county_parcel_id")
                                        matched = True
                                    elif re.search(r'account number', norm_k):
                                        result['tax_id'] = value
                                        print(f"      -> Matched to tax_id")
                                        matched = True
                                    elif re.search(r'property address', norm_k) or re.search(r'street address', norm_k):
                                        result['physical_address'] = value
                                        print(f"      -> Matched to physical_address")
                                        matched = True
                                    elif re.search(r'mailing address', norm_k):
                                        result['mailing_address'] = value
                                        print(f"      -> Matched to mailing_address")
                                        matched = True
                                    elif re.search(r'owner name', norm_k) or re.search(r'primary owner', norm_k):
                                        result['owner_name'] = value
                                        print(f"      -> Matched to owner_name")
                                        matched = True
                                    elif re.search(r'tax district', norm_k):
                                        result['tax_district'] = value
                                        print(f"      -> Matched to tax_district")
                                        matched = True
                                    elif re.search(r'total acres', norm_k) or re.search(r'acres', norm_k):
                                        result['total_acres'] = value
                                        print(f"      -> Matched to total_acres")
                                        matched = True
                                    elif re.search(r'legal description', norm_k) or re.search(r'extended legal', norm_k):
                                        result['legal']['location'] = value
                                        print(f"      -> Matched to legal.location")
                                        matched = True
                                    elif re.search(r'subdivision', norm_k):
                                        result['legal']['subdivision'] = value
                                        print(f"      -> Matched to legal.subdivision")
                                        matched = True
                                    elif re.search(r'deed', norm_k):
                                        result['deed'] = value
                                        print(f"      -> Matched to deed")
                                        matched = True
                                    elif re.search(r'land', norm_k):
                                        result['value_summary']['land'] = value
                                        print(f"      -> Matched to land value")
                                        matched = True
                                    elif re.search(r'improvement', norm_k):
                                        result['value_summary']['developments'] = value
                                        print(f"      -> Matched to developments value")
                                        matched = True
                                    elif re.search(r'total', norm_k):
                                        result['value_summary']['total_value'] = value
                                        print(f"      -> Matched to total value")
                                        matched = True
                                    # Handle acreage breakdown
                                    elif 'residential' in norm_k:
                                        result['acreage_breakdown']['residential'] = float(value) if value.replace('.', '').isdigit() else value
                                        print(f"      -> Matched residential acreage: {value}")
                                        matched = True
                                    elif 'agricultural' in norm_k:
                                        result['acreage_breakdown']['agricultural'] = float(value) if value.replace('.', '').isdigit() else value
                                        print(f"      -> Matched agricultural acreage: {value}")
                                        matched = True
                                    elif 'commercial' in norm_k:
                                        result['acreage_breakdown']['commercial'] = float(value) if value.replace('.', '').isdigit() else value
                                        print(f"      -> Matched commercial acreage: {value}")
                                        matched = True
                                    elif 'industrial' in norm_k:
                                        result['acreage_breakdown']['industrial'] = float(value) if value.replace('.', '').isdigit() else value
                                        print(f"      -> Matched industrial acreage: {value}")
                                        matched = True
                                    elif 'other' in norm_k or 'misc' in norm_k or 'mixed' in norm_k:
                                        result['acreage_breakdown']['other'] = float(value) if value.replace('.', '').isdigit() else value
                                        print(f"      -> Matched other acreage: {value}")
                                        matched = True
                                    
                                    if matched:
                                        break
                                
                                if matched:
                                    break
            
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
            
            elif source_name == 'divs':
                # Process div-based data
                print(f"  Processing divs: {source_data}")
                for k, v in source_data.items():
                    print(f"    [DIV] Key: {k}, Value: {v}")
                    if k == 'Property Address':
                        result['physical_address'] = v
                        print(f"      -> Matched to physical_address")
                    elif k == 'Primary Owner':
                        result['owner_name'] = v
                        print(f"      -> Matched to owner_name")
                    elif k == 'Mailing Address':
                        result['mailing_address'] = v
                        print(f"      -> Matched to mailing_address")
                    elif k == 'Extended Legal':
                        result['legal']['location'] = v
                        print(f"      -> Matched to legal.location")
            
            elif source_name == 'definition_lists':
                # Process definition list data
                print(f"  Processing definition lists: {source_data}")
                for k, v in source_data.items():
                    norm_k = self.normalize_key(k)
                    print(f"    [DL] Key: {k} (norm: {norm_k}), Value: {v}")
                    
                    # Map legal description fields
                    if norm_k == 'subdivision':
                        result['legal']['subdivision'] = v
                        print(f"      -> Matched to legal.subdivision")
                    elif norm_k == 'lot':
                        result['legal']['lot'] = v
                        print(f"      -> Matched to legal.lot")
                    elif norm_k == 'block':
                        result['legal']['block'] = v
                        print(f"      -> Matched to legal.block")
                    elif norm_k == 'section':
                        result['legal']['section'] = v
                        print(f"      -> Matched to legal.section")
                    elif norm_k == 'township':
                        result['legal']['township'] = v
                        print(f"      -> Matched to legal.township")
                    elif norm_k == 'range':
                        result['legal']['range'] = v
                        print(f"      -> Matched to legal.range")
                    
                    # Map property information fields
                    elif 'parcel number' in norm_k:
                        result['county_parcel_id'] = v
                        print(f"      -> Matched to county_parcel_id")
                    elif 'account number' in norm_k:
                        # Extract just the account number, not the link
                        account_match = re.search(r'([A-Z0-9]+)', v)
                        if account_match:
                            result['tax_id'] = account_match.group(1)
                            print(f"      -> Matched to tax_id: {account_match.group(1)}")
                    elif 'tax district' in norm_k:
                        result['tax_district'] = v
                        print(f"      -> Matched to tax_district")
                    elif 'total acres' in norm_k:
                        result['total_acres'] = v
                        print(f"      -> Matched to total_acres")
                    elif 'square feet' in norm_k:
                        print(f"      -> Found square feet: {v}")
                    elif 'current mill levy' in norm_k:
                        print(f"      -> Found mill levy: {v}")
            
            elif source_name == 'buildings':
                # Process building data into flat structure
                print(f"  Processing buildings: {len(source_data)} buildings found")
                for building in source_data:
                    print(f"    [BUILDING] {building}")
                    
                    # Option 1: Create a flattened building structure (simple dict)
                    flat_building = {}
                    
                    # Add ALL attributes to the flat structure (including empty ones)
                    print(f"      -> Adding building: {building.items()}")
                    for key, value in building.items():
                        flat_building[key] = value  # Include ALL attributes, even empty ones
                    
                    # Option 2: Create list of tuples format
                    # Uncomment this section if you prefer tuples format:
                    # attribute_tuples = []
                    # for key, value in building.items():
                    #     if value:  # Only include non-empty values
                    #         attribute_tuples.append((key, value))
                    # flat_building = {
                    #     'Building Name': building.get('Building Name', 'Unknown'),
                    #     'attributes': attribute_tuples
                    # }
                    
                    developments.append(flat_building)
                    print(f"    -> Flattened: {flat_building}")
        
        # Add developments to the canonical structure
        result['developments'] = developments
        
        return result

def scrape_property_details(url: str, config: dict = None) -> dict:
    """Instantiate and use the Lincoln-specific PropertyDetailsScraper."""
    scraper = LincolnPropertyDetailsScraper(url, config)
    return scraper.scrape()
