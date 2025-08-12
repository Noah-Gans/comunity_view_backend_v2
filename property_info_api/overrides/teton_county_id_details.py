"""Overrides for Teton County Idaho scraping logic."""
import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path
import logging
from config import TETON_IDAHO_DB_PATH

logger = logging.getLogger(__name__)

def scrape_tax(url: str) -> dict:
    """Override Teton County Idaho tax scraper."""
    return {"override": True, "county": "Teton Idaho", "type": "tax", "url": url}

def scrape_clerk(url: str) -> dict:
    """Override Teton County Idaho clerk scraper."""
    return {"override": True, "county": "Teton Idaho", "type": "clerk", "url": url}

class TetonIdahoPropertyDetailsScraper:
    """Scraper for Teton County Idaho property details using processed database."""
    
    def __init__(self, url: str):
        self.url = url
        self.parcel_id = self.extract_parcel_id_from_url()
        self.database_path = Path(TETON_IDAHO_DB_PATH)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        
    def extract_parcel_id_from_url(self) -> str:
        """Extract parcel ID from URL or use default for testing."""
        # Try to extract from URL if present
        match = re.search(r'parcel[_-]?id=([^&]+)', self.url, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try other common patterns
        match = re.search(r'account[_-]?no=([^&]+)', self.url, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # For testing, return None to use sample data
        return None
    
    def get_parcel_data(self, parcel_id: str) -> dict:
        """Retrieve parcel data from SQLite database."""
        if not self.database_path.exists():
            logger.error(f"Database not found: {self.database_path}")
            return None
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get basic parcel information
            cursor.execute('''
                SELECT * FROM parcels 
                WHERE county_parcel_id = ?
            ''', (parcel_id,))
            
            parcel_row = cursor.fetchone()
            if not parcel_row:
                logger.warning(f"Parcel not found: {parcel_id}")
                return None
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            parcel_data = dict(zip(columns, parcel_row))
            
            # Get improvements
            cursor.execute('''
                SELECT * FROM improvements 
                WHERE county_parcel_id = ?
                ORDER BY improvement_number
            ''', (parcel_id,))
            
            improvements = []
            for row in cursor.fetchall():
                imp_columns = [description[0] for description in cursor.description]
                improvements.append(dict(zip(imp_columns, row)))
            
            # Get legal descriptions
            cursor.execute('''
                SELECT * FROM legal_descriptions 
                WHERE county_parcel_id = ?
            ''', (parcel_id,))
            
            legal_descriptions = []
            for row in cursor.fetchall():
                legal_columns = [description[0] for description in cursor.description]
                legal_descriptions.append(dict(zip(legal_columns, row)))
            
            # Get land records
            cursor.execute('''
                SELECT * FROM land_records 
                WHERE county_parcel_id = ?
                ORDER BY land_category
            ''', (parcel_id,))
            
            land_records = []
            for row in cursor.fetchall():
                land_columns = [description[0] for description in cursor.description]
                land_records.append(dict(zip(land_columns, row)))
            
            # Get sales history
            cursor.execute('''
                SELECT * FROM sales 
                WHERE county_parcel_id = ?
                ORDER BY sale_date DESC
            ''', (parcel_id,))
            
            sales = []
            for row in cursor.fetchall():
                sales_columns = [description[0] for description in cursor.description]
                sales.append(dict(zip(sales_columns, row)))
            
            # Get permits
            cursor.execute('''
                SELECT * FROM permits 
                WHERE county_parcel_id = ?
                ORDER BY permit_filing_date DESC
            ''', (parcel_id,))
            
            permits = []
            for row in cursor.fetchall():
                permit_columns = [description[0] for description in cursor.description]
                permits.append(dict(zip(permit_columns, row)))
            
            conn.close()
            
            return {
                'parcel': parcel_data,
                'improvements': improvements,
                'legal_descriptions': legal_descriptions,
                'land_records': land_records,
                'sales': sales,
                'permits': permits
            }
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            return None
    
    def map_to_canonical(self, parcel_data: dict) -> dict:
        """Map Teton County Idaho data to our canonical structure."""
        if not parcel_data:
            return {"error": "No parcel data found"}
        
        # Load canonical structure
        with open('property_info_api/structure.json') as f:
            canonical = json.load(f)
        
        result = canonical.copy()
        parcel = parcel_data['parcel']
        
        # Map basic fields
        result['county_parcel_id'] = parcel.get('county_parcel_id', '')
        result['tax_id'] = parcel.get('deed_reference1', '')  # Use deed reference as tax ID
        result['physical_address'] = parcel.get('physical_address', '')
        
        # Format mailing address
        mailing_parts = []
        if parcel.get('mailing_address_line1'):
            mailing_parts.append(parcel['mailing_address_line1'])
        if parcel.get('mailing_address_line2'):
            mailing_parts.append(parcel['mailing_address_line2'])
        if parcel.get('mailing_city'):
            mailing_parts.append(parcel['mailing_city'])
        if parcel.get('mailing_state'):
            mailing_parts.append(parcel['mailing_state'])
        if parcel.get('mailing_zip'):
            mailing_parts.append(parcel['mailing_zip'])
        
        result['mailing_address'] = ', '.join(mailing_parts)
        result['owner_name'] = parcel.get('owner_name', '')
        
        # Combine deed references
        deed_refs = []
        for i in range(1, 6):
            ref = parcel.get(f'deed_reference{i}', '')
            if ref:
                deed_refs.append(ref)
        result['deed'] = '; '.join(deed_refs)
        
        # Map legal description
        if parcel_data['legal_descriptions']:
            legal = parcel_data['legal_descriptions'][0]
            legal_lines = []
            for i in range(1, 7):
                line = legal.get(f'legal_line{i}', '')
                if line:
                    legal_lines.append(line)
            result['legal']['location'] = ' '.join(legal_lines)
        
        result['tax_district'] = parcel.get('tax_district', '')
        result['total_acres'] = str(parcel.get('total_acres', ''))
        
        # Map value summary
        result['value_summary']['total_value'] = str(parcel.get('total_value', ''))
        result['value_summary']['land'] = str(parcel.get('land_value', ''))
        result['value_summary']['developments'] = str(parcel.get('improvement_value', ''))
        
        # Process improvements as developments with ALL available fields
        developments = []
        for improvement in parcel_data['improvements']:
            development = {
                # Basic identification
                'Building ID': improvement.get('improvement_number', ''),
                'Property Type': improvement.get('dwelling_type', ''),
                'Property Address': improvement.get('property_address', ''),
                
                # Construction details
                'Year Built': improvement.get('year_built', ''),
                'Effective Year': improvement.get('effective_year', ''),
                'Stories': improvement.get('stories', ''),
                'Units': improvement.get('units', ''),
                'Market Grade': improvement.get('market_grade', ''),
                'Class': improvement.get('class', ''),
                'Use Code': improvement.get('use_code', ''),
                
                # Physical characteristics
                'Bedrooms': improvement.get('bedrooms', ''),
                'Bathrooms': improvement.get('bathrooms', ''),
                'Rooms': improvement.get('rooms', ''),
                'Fireplaces': improvement.get('fireplaces', ''),
                
                # Square footage breakdown
                'Total Sq Ft': improvement.get('total_sqft', ''),
                'First Floor Sq Ft': improvement.get('first_floor_sqft', ''),
                'Second Floor Sq Ft': improvement.get('second_floor_sqft', ''),
                'Basement Sq Ft': improvement.get('basement_sqft', ''),
                'Attic Sq Ft': improvement.get('attic_sqft', ''),
                'Garage 1 Sq Ft': improvement.get('garage1_sqft', ''),
                'Garage 2 Sq Ft': improvement.get('garage2_sqft', ''),
                
                # Construction materials
                'Siding': improvement.get('siding', ''),
                'Roofing': improvement.get('roofing', ''),
                'Exterior': improvement.get('exterior', ''),
                'Interior': improvement.get('interior', ''),
                'Foundation': improvement.get('foundation', ''),
                'Floor Cover': improvement.get('floor_cover', ''),
                
                # Mechanical systems
                'Heating System 1': improvement.get('heating_system1', ''),
                'Heating System 2': improvement.get('heating_system2', ''),
                'Heating System 3': improvement.get('heating_system3', ''),
                'Fuel Gas': improvement.get('fuel_gas', ''),
                'Fuel Oil': improvement.get('fuel_oil', ''),
                'Fuel Electric': improvement.get('fuel_electric', ''),
                'Fuel Solid': improvement.get('fuel_solid', ''),
                
                # Valuation
                'Improvement Value': improvement.get('improvement_value', ''),
                'Estimated Value': improvement.get('estimated_value', ''),
                'Base Cost': improvement.get('base_cost', ''),
                'Percent Complete': improvement.get('percent_complete', ''),
                
                # Additional details
                'Conforming': improvement.get('conforming', ''),
                'Other Improvements Only': improvement.get('other_improvements_only', ''),
                'Review Year': improvement.get('review_year', ''),
                'Inspection Date': improvement.get('inspection_date', ''),
                'Appraiser Initials': improvement.get('appraiser_initials', ''),
                'Line Number': improvement.get('line_number', ''),
                'House Number 1': improvement.get('house_number1', ''),
                'House Number 2': improvement.get('house_number2', ''),
                'Direction 1': improvement.get('direction1', ''),
                'Street Name': improvement.get('street_name', ''),
                'Direction 2': improvement.get('direction2', ''),
                'Zip Code': improvement.get('zip_code', '')
            }
            
            # Remove empty values
            development = {k: v for k, v in development.items() if v is not None and v != ''}
            developments.append(development)
        
        result['developments'] = developments
        
        # Process land records for acreage breakdown with detailed information
        acreage_breakdown = {
            'residential': 0.0,
            'agricultural': 0.0,
            'commercial': 0.0,
            'industrial': 0.0,
            'other': 0.0
        }
        
        # Store detailed land records
        detailed_land_records = []
        for land_record in parcel_data['land_records']:
            land_category = land_record.get('land_category', 0)
            land_quantity = land_record.get('land_quantity', 0) or 0
            
            # Map land categories to our breakdown
            if land_category in [1, 2, 3]:  # Residential categories
                acreage_breakdown['residential'] += land_quantity
            elif land_category in [4, 5, 6]:  # Agricultural categories
                acreage_breakdown['agricultural'] += land_quantity
            elif land_category in [7, 8, 9]:  # Commercial categories
                acreage_breakdown['commercial'] += land_quantity
            elif land_category in [10, 11, 12]:  # Industrial categories
                acreage_breakdown['industrial'] += land_quantity
            else:
                acreage_breakdown['other'] += land_quantity
            
            # Store detailed record
            detailed_land_records.append({
                'Land Category': land_record.get('land_category', ''),
                'Land Quantity': land_record.get('land_quantity', ''),
                'Land Unit': land_record.get('land_unit', ''),
                'Land Value': land_record.get('land_value', ''),
                'Location Number': land_record.get('location_number', ''),
                'Class Number': land_record.get('class_number', ''),
                'Type Number': land_record.get('type_number', ''),
                'Record Number': land_record.get('record_number', ''),
                'Appraiser Initials': land_record.get('appraiser_initials', ''),
                'Appraisal Date': land_record.get('appraisal_date', ''),
                'Review Year': land_record.get('review_year', '')
            })
        
        result['acreage_breakdown'] = acreage_breakdown
        result['detailed_land_records'] = detailed_land_records
        
        # Add sales history
        if parcel_data.get('sales'):
            sales_history = []
            for sale in parcel_data['sales']:
                sales_history.append({
                    'Sale Date': sale.get('sale_date', ''),
                    'Valid Sale': sale.get('valid_sale', ''),
                    'Selling Price': sale.get('selling_price', ''),
                    'Personal Property': sale.get('personal_property', ''),
                    'Constant Sales Designator': sale.get('constant_sales_designator', '')
                })
            result['sales_history'] = sales_history
        
        # Add permits
        if parcel_data.get('permits'):
            building_permits = []
            for permit in parcel_data['permits']:
                building_permits.append({
                    'Permit Reference Number': permit.get('permit_ref_number', ''),
                    'Field Visit Record': permit.get('field_visit_record', ''),
                    'Filing Date': permit.get('filing_date', ''),
                    'Callback Date': permit.get('callback_date', ''),
                    'Inactive Date': permit.get('inactive_date', ''),
                    'Certified Date': permit.get('certified_date', ''),
                    'Description': permit.get('description', ''),
                    'Permit Type': permit.get('permit_type', ''),
                    'Permit Source': permit.get('permit_source', ''),
                    'Contact Number': permit.get('contact_number', '')
                })
            result['building_permits'] = building_permits
        
        return result
    
    def write_debug_files(self, parcel_data: dict, canonical_data: dict):
        """Write debug files for troubleshooting."""
        # Write raw parcel data
        raw_filename = f'property_details_teton_id_raw_{self.timestamp}.json'
        with open(raw_filename, 'w', encoding='utf-8') as f:
            json.dump(parcel_data, f, indent=2, ensure_ascii=False)
        
        # Write canonical data
        canonical_filename = f'property_details_teton_id_canonical_{self.timestamp}.json'
        with open(canonical_filename, 'w', encoding='utf-8') as f:
            json.dump(canonical_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Debug files written: {raw_filename}, {canonical_filename}")
    
    def scrape(self) -> dict:
        """Main scraping method for Teton County Idaho."""
        logger.info(f"Scraping Teton County Idaho parcel: {self.parcel_id}")
        
        # Get parcel data from database
        parcel_data = self.get_parcel_data(self.parcel_id)
        
        if not parcel_data:
            return {
                "error": "Parcel not found",
                "county": "Teton Idaho",
                "parcel_id": self.parcel_id
            }
        
        # Map to canonical structure
        canonical_data = self.map_to_canonical(parcel_data)
        
        # Write debug files
        self.write_debug_files(parcel_data, canonical_data)
        
        # Add metadata
        canonical_data['county'] = 'Teton Idaho'
        canonical_data['source'] = 'teton_county_id_details'
        canonical_data['parcel_id'] = self.parcel_id
        canonical_data['database_source'] = True
        
        return canonical_data

def scrape_property_details(url: str) -> dict:
    """Main entry point for Teton County Idaho property details scraping."""
    scraper = TetonIdahoPropertyDetailsScraper(url)
    return scraper.scrape() 