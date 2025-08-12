"""Overrides for Teton County scraping logic."""
import requests
import json
import time
import re
from datetime import datetime
import copy

def scrape_tax(url: str) -> dict:
    """Override Teton County tax scraper."""
    return {"override": True, "county": "Teton", "type": "tax", "url": url}

def scrape_clerk(url: str) -> dict:
    """Override Teton County clerk scraper."""
    return {"override": True, "county": "Teton", "type": "clerk", "url": url}

class TetonPropertyDetailsScraper:
    """Scraper for Teton County property details using direct ArcGIS REST API calls."""
    
    def __init__(self, url: str):
        self.url = url
        self.accountno = self.extract_accountno_from_url()
        self.base_url = "https://gis.tetoncountywy.gov/server/rest/services/Public_Services/Parcels/FeatureServer"
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        
    def extract_accountno_from_url(self) -> str:
        """Extract account number from URL or use default for testing."""
        # Try to extract from URL if present
        match = re.search(r'accountno=([^&]+)', self.url)
        if match:
            return match.group(1)
        # For testing, use the example account number
        return "R0008450"
    
    def call_arcgis_api(self, layer: int) -> dict:
        """Call ArcGIS REST API for a specific layer."""
        url = f"{self.base_url}/{layer}/query"
        params = {
            'f': 'json',
            'outFields': '*',
            'where': f"accountno='{self.accountno}'"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[TETON] Error calling layer {layer}: {e}")
            return {"features": []}
    
    def write_api_data_to_file(self, data: dict, layer: int):
        """Write API response data to a file for debugging."""
        filename = f'property_details_teton_layer_{layer}_{self.timestamp}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[TETON] Layer {layer} data saved to: {filename}")
    
    def scrape(self) -> dict:
        """Main scraping method for Teton County."""
        print(f"[TETON] Scraping account: {self.accountno}")
        
        # Call all three layers
        layer_0_data = self.call_arcgis_api(0)  # General parcel info
        layer_2_data = self.call_arcgis_api(2)  # Property details (buildings)
        layer_3_data = self.call_arcgis_api(3)  # Land details (acreage)
        
        # Write data to files for debugging
        self.write_api_data_to_file(layer_0_data, 0)
        self.write_api_data_to_file(layer_2_data, 2)
        self.write_api_data_to_file(layer_3_data, 3)
        
        # Map to canonical structure
        result = self.map_to_canonical(layer_0_data, layer_2_data, layer_3_data)
        
        # Write final result to file
        filename = f'property_details_teton_final_{self.timestamp}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"[TETON] Final result saved to: {filename}")
        
        return result
    
    def map_to_canonical(self, layer_0_data: dict, layer_2_data: dict, layer_3_data: dict) -> dict:
        """Map ArcGIS data to our canonical structure."""
        # Load canonical structure
        with open('property_info_api/structure.json') as f:
            canonical = json.load(f)
        
        result = copy.deepcopy(canonical)
        
        # Process Layer 0 (General parcel info)
        if layer_0_data.get('features'):
            parcel_data = layer_0_data['features'][0]['attributes']
            print(f"[TETON] Processing parcel data: {parcel_data}")
            
            # Map basic fields
            result['county_parcel_id'] = parcel_data.get('pidn', '')
            result['tax_id'] = parcel_data.get('tax_id', '')
            result['physical_address'] = parcel_data.get('st_address', '')
            result['mailing_address'] = self.format_mailing_address(parcel_data)
            result['owner_name'] = parcel_data.get('owner', '')
            result['deed'] = parcel_data.get('deed', '')
            result['tax_district'] = parcel_data.get('tax_dist', '')
            result['total_acres'] = str(parcel_data.get('area_tax', ''))
            
            # Map legal fields
            result['legal']['subdivision'] = self.extract_subdivision(parcel_data.get('descript', ''))
            result['legal']['lot'] = parcel_data.get('lot', '')
            result['legal']['block'] = self.extract_block(parcel_data.get('descript', ''))
            result['legal']['section'] = self.extract_section(parcel_data.get('descript', ''))
            result['legal']['township'] = self.extract_township(parcel_data.get('descript', ''))
            result['legal']['range'] = self.extract_range(parcel_data.get('descript', ''))
            result['legal']['location'] = parcel_data.get('descript', '')
            
            # Map value summary
            result['value_summary']['total_value'] = str(parcel_data.get('acctval', ''))
            result['value_summary']['land'] = str(parcel_data.get('landval', ''))
            result['value_summary']['developments'] = str(parcel_data.get('impsval', ''))
        
        # Process Layer 2 (Property details/buildings)
        if layer_2_data.get('features'):
            buildings_data = layer_2_data['features']
            print(f"[TETON] Processing {len(buildings_data)} buildings")
            
            for building in buildings_data:
                building_attrs = building['attributes']
                print(f"[TETON] Processing building: {building_attrs}")
                
                # Create flat building structure with all attributes
                flat_building = {
                    'Building ID': building_attrs.get('impno', ''),
                    'Account Number': building_attrs.get('accountno', ''),
                    'Neighborhood': building_attrs.get('nbhd', ''),
                    'Improvement Value': building_attrs.get('impsval', ''),
                    'Build Date ID': building_attrs.get('builddateid', ''),
                    'Parcel Number': building_attrs.get('parcelno', ''),
                    'Improvement ID': building_attrs.get('bltasdetailid', ''),
                    'Jurisdiction': building_attrs.get('jurisdiction', ''),
                    'Property Type': building_attrs.get('propertytype', ''),
                    'Owner Occupied Flag': building_attrs.get('owneroccupiedflag', ''),
                    'Occupancy Code': building_attrs.get('occcode', ''),
                    'Occupancy Description': building_attrs.get('occdescription', ''),
                    'BLTAS Code': building_attrs.get('bltascode', ''),
                    'BLTAS Description': building_attrs.get('bltasdescription', ''),
                    'Square Feet': building_attrs.get('sf', ''),
                    'Condo Improvement SF': building_attrs.get('condoimpsf', ''),
                    'Basement SF': building_attrs.get('basementsf', ''),
                    'Improvement Perimeter': building_attrs.get('impperimeter', ''),
                    'Improvement Completed %': building_attrs.get('impcompletedpct', ''),
                    'Improvement Condition Type': building_attrs.get('impconditiontype', ''),
                    'Improvement Quality': building_attrs.get('impquality', ''),
                    'HVAC Type': building_attrs.get('hvactype', ''),
                    'Improvement Exterior': building_attrs.get('impexterior', ''),
                    'Improvement Interior': building_attrs.get('impinterior', ''),
                    'Improvement Unit Type': building_attrs.get('impunittype', ''),
                    'BLTAS Stories': building_attrs.get('bltasstories', ''),
                    'Sprinkler SF': building_attrs.get('sprinklersf', ''),
                    'Roof Type': building_attrs.get('rooftype', ''),
                    'Roof Cover': building_attrs.get('roofcover', ''),
                    'Floor Cover': building_attrs.get('floorcover', ''),
                    'BLTAS Foundation': building_attrs.get('bltasfoundation', ''),
                    'Room Count': building_attrs.get('roomcount', ''),
                    'Bedroom Count': building_attrs.get('bedroomcount', ''),
                    'Bath Count': building_attrs.get('bathcount', ''),
                    'BLTAS Total Unit Count': building_attrs.get('bltastotalunitcount', ''),
                    'Class Code': building_attrs.get('classcode', ''),
                    'Class Description': building_attrs.get('classdescription', ''),
                    'BLTAS Year Built': building_attrs.get('bltasyearbuilt', ''),
                    'Year Remodeled': building_attrs.get('yearremodeled', ''),
                    'Remodeled Percent': building_attrs.get('remodeledpercent', ''),
                    'Adjusted Year Built': building_attrs.get('adjustedyearbuilt', ''),
                    'Age': building_attrs.get('age', ''),
                    'Mobile Home Title No': building_attrs.get('mhtitleno', ''),
                    'Mobile Home Serial No': building_attrs.get('mhserialno', ''),
                    'Mobile Home Length': building_attrs.get('mhlength', ''),
                    'Mobile Home Width': building_attrs.get('mhwidth', ''),
                    'Mobile Home Code': building_attrs.get('mhcode', ''),
                    'Appraiser': building_attrs.get('appraiser', ''),
                    'Appraisal Date': building_attrs.get('appraisaldate', ''),
                    'New Construction Value': building_attrs.get('newconstructionvalue', ''),
                    'Permit Value Change': building_attrs.get('permitvaluechange', ''),
                    'Occupancy Percent': building_attrs.get('occpercent', ''),
                    'Occupancy Abstract': building_attrs.get('occabstract', ''),
                    'Net SF': building_attrs.get('netsf', ''),
                    'Last Update Timestamp': building_attrs.get('lastupdatetimestamp', ''),
                    'Mobile Home Model Name': building_attrs.get('mhmodelname', ''),
                    'Mobile Home Total Length': building_attrs.get('mhtotallength', ''),
                    'Mobile Home Decal No': building_attrs.get('mhdecalno', ''),
                    'Mobile Home Tag No': building_attrs.get('mhtagno', ''),
                    'Neighborhood Extension': building_attrs.get('nbhdextension', ''),
                    'Total Unfinished SF': building_attrs.get('totalunfinishedsf', ''),
                    'Total Finished SF': building_attrs.get('totalfinishedsf', ''),
                    'Cost RCN': building_attrs.get('costrcn', ''),
                    'Cost RCNLD': building_attrs.get('costrcnld', ''),
                    'Detail Unit Count': building_attrs.get('detailunitcount', ''),
                    'Improvement Detail Description': building_attrs.get('impdetaildescription', ''),
                    'Improvement Detail Type': building_attrs.get('impdetailtype', '')
                }
                
                # Remove empty values for cleaner output
                flat_building = {k: v for k, v in flat_building.items() if v is not None and v != ''}
                
                result['developments'].append(flat_building)
        
        # Process Layer 3 (Land details/acreage breakdown)
        if layer_3_data.get('features'):
            land_data = layer_3_data['features'][0]['attributes']
            print(f"[TETON] Processing land data: {land_data}")
            
            land_type = land_data.get('landtype', '').lower()
            land_acres = land_data.get('landacres', 0)
            
            # Map to acreage breakdown based on land type
            if 'residential' in land_type:
                result['acreage_breakdown']['residential'] = land_acres
            elif 'agricultural' in land_type:
                result['acreage_breakdown']['agricultural'] = land_acres
            elif 'commercial' in land_type:
                result['acreage_breakdown']['commercial'] = land_acres
            elif 'industrial' in land_type:
                result['acreage_breakdown']['industrial'] = land_acres
            else:
                result['acreage_breakdown']['other'] = land_acres
        
        return result
    
    def format_mailing_address(self, parcel_data: dict) -> str:
        """Format mailing address from parcel data."""
        address = parcel_data.get('address', '')
        address2 = parcel_data.get('address2', '')
        city = parcel_data.get('owner_city', '')
        state = parcel_data.get('owner_state', '')
        zip_code = parcel_data.get('owner_zip', '')
        
        parts = [part for part in [address, address2, city, state, zip_code] if part]
        return ', '.join(parts) if parts else ''
    
    def extract_subdivision(self, description: str) -> str:
        """Extract subdivision from legal description."""
        if not description:
            return ''
        # Look for patterns like "LOT 12, H-H-R RANCHES"
        match = re.search(r'LOT\s+\d+,\s+([^,]+)', description, re.IGNORECASE)
        return match.group(1).strip() if match else ''
    
    def extract_block(self, description: str) -> str:
        """Extract block from legal description."""
        if not description:
            return ''
        # Look for patterns like "BLOCK 7" or "B 07"
        match = re.search(r'BLOCK\s+(\d+)', description, re.IGNORECASE)
        return match.group(1) if match else ''
    
    def extract_section(self, description: str) -> str:
        """Extract section from legal description."""
        if not description:
            return ''
        # Look for patterns like "S25" or "SECTION 25"
        match = re.search(r'S(\d+)', description, re.IGNORECASE)
        return match.group(1) if match else ''
    
    def extract_township(self, description: str) -> str:
        """Extract township from legal description."""
        if not description:
            return ''
        # Look for patterns like "T32" or "TOWNSHIP 32"
        match = re.search(r'T(\d+)', description, re.IGNORECASE)
        return match.group(1) if match else ''
    
    def extract_range(self, description: str) -> str:
        """Extract range from legal description."""
        if not description:
            return ''
        # Look for patterns like "R119" or "RANGE 119"
        match = re.search(r'R(\d+)', description, re.IGNORECASE)
        return match.group(1) if match else ''

def scrape_property_details(url: str) -> dict:
    """Main entry point for Teton County property details scraping."""
    scraper = TetonPropertyDetailsScraper(url)
    return scraper.scrape() 