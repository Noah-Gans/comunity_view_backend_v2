"""Centralized data standardization for consistent API responses."""
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

class DataStandardizer:
    """Standardizes all API responses into a consistent format."""
    
    def __init__(self, config_dir="property_info_api/configs", raw_data=None, county=None):
        self.configs = self._load_configs(config_dir)
        self.raw_data = raw_data
        self.county = county  # Store county as instance attribute
    
    def _load_configs(self, config_dir):
        """Load all county configs."""
        configs = {}
        if os.path.exists(config_dir):
            for config_file in os.listdir(config_dir):
                if config_file.endswith('.json'):
                    county = config_file.replace('.json', '')
                    with open(f"{config_dir}/{config_file}") as f:
                        configs[county] = json.load(f)
        return configs
    
    def extract_field(self, field_name: str, data_sources: Dict) -> Optional[Any]:
        """Extract a field using county-specific mapping config from ALL sections."""
        config = self.configs.get(self.county, {})  # Use self.county
        all_mappings = config.get("mappings", {})
        
        # Check if the field exists in the top-level mappings (new structure)
        if field_name in all_mappings:
            field_config = all_mappings[field_name]
            sources = field_config.get("sources", [])
        else:
            # Fallback to old structure for backward compatibility
            sources = []
            for section_name, section_mappings in all_mappings.items():
                if field_name in section_mappings:
                    field_config = section_mappings[field_name]
                    sources.extend(field_config.get("sources", []))
        
        if not sources:
            return None
        
        # Try sources in priority order
        for source in sorted(sources, key=lambda x: x["priority"]):
            if source["path"] == "null":
                return None
            if source["path"] == "hardcoded":
                return source.get("value")
                
            value = self._get_nested_value(data_sources, source["path"])
            if value is not None:
                # Apply transformation if specified
                if "transform" in source:
                    value = self._apply_transform(value, source, data_sources)

                return value
        
        return None
    
    def _get_nested_value(self, data: Dict, path: str) -> Optional[Any]:
        """Get value from nested dictionary using dot notation."""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _apply_transform(self, value: Any, source_config: Dict, data_sources: Dict) -> Any:
        """Apply transformation to extracted value."""
        transform_name = source_config.get("transform")

        if not transform_name:
            return value
        
        try:
            if transform_name == "format_county_state":
                return self._format_county_state(value)
            elif transform_name == "standardize_historical":
                return self._standardize_historical_data(value)
            elif transform_name == "format_acreage_breakdown":
                return self._format_acreage_breakdown(value)
            elif transform_name == "count_developments":
                return self._count_developments(value)
            elif transform_name == "standardize_developments":
                return self._standardize_developments(value)
            elif transform_name == "flatten_first_half":
                return self._flatten_first_half(value)
            elif transform_name == "flatten_second_half":
                return self._flatten_second_half(value)
            elif transform_name == "divide_by_two":
                return float(value) / 2 if value else 0
            elif transform_name == "add_two_fields":
                # Format: "add_two_fields:field1,field2"
                fields_to_add = source_config.get("fields_to_add", [])
                print("camer here with fields: ", fields_to_add)

                if len(fields_to_add) == 2:
                    print("came here with fields: ", fields_to_add)
                    field1_val = self.extract_field(fields_to_add[0], data_sources)
                    field2_val = self.extract_field(fields_to_add[1], data_sources)
                    val1 = float(field1_val) if field1_val else 0
                    val2 = float(field2_val) if field2_val else 0
                    return val1 + val2
                return 0
            elif transform_name == "calculate_amount_due":
                if data_sources:
                    tax_levied = self.extract_field("tax_levied", data_sources)
                    tax_paid = self.extract_field("tax_paid", data_sources)
                    levied_val = float(tax_levied) if tax_levied else 0
                    paid_val = float(tax_paid) if tax_paid else 0
                    return max(0, levied_val - paid_val)
                return 0
            elif transform_name == "calculate_first_half_due":
                if data_sources:
                    first_half_levied = self.extract_field("first_half_tax_levied", data_sources)
                    first_half_paid = self.extract_field("first_half_tax_paid", data_sources)
                    levied_val = float(first_half_levied) if first_half_levied else 0
                    paid_val = float(first_half_paid) if first_half_paid else 0
                    return max(0, levied_val - paid_val)
                return 0
            elif transform_name == "calculate_second_half_due":
                if data_sources:
                    second_half_levied = self.extract_field("second_half_tax_levied", data_sources)
                    second_half_paid = self.extract_field("second_half_tax_paid", data_sources)
                    levied_val = float(second_half_levied) if second_half_levied else 0
                    paid_val = float(second_half_paid) if second_half_paid else 0
                    return max(0, levied_val - paid_val)
                return 0
            elif transform_name == "calculate_lincoln_amount_due":
                bill_amount = float(self._get_nested_value(self.raw_data, "historical_record.bill_amount"))
                first_half_paid = float(self._get_nested_value(self.raw_data, "historical_record.first_half_paid_amount"))
                second_half_paid = float(value) if value else 0
                return bill_amount - first_half_paid - second_half_paid
            else:
                print(f"[DataStandardizer] Unknown transform: {transform_name}")
                return value
        except Exception as e:
            print(f"[DataStandardizer] Error applying transform {transform_name}: {str(e)}")
            return value

    def _format_county_state(self, county: str) -> str:
        """Format county string to county, state format."""
        county_clean = county.replace("_", " ").title()
        
        # Map county names to states
        state_mapping = {
            "Fremont County Wy": "Fremont County, WY",
            "Sublette County Wy": "Sublette County, WY", 
            "Lincoln County Wy": "Lincoln County, WY",
            "Teton County Wy": "Teton County, WY",
            "Teton County Id": "Teton County, ID"
        }
        
        return state_mapping.get(county_clean, county_clean)
    
    def _standardize_historical_data(self, historical_data: List[Dict]) -> List[Dict]:
        """Standardize historical data using config-driven field extraction."""
        if not historical_data:
            return []
        
        standardized_historical = []
        for record in historical_data:
            # Create virtual data source for this single historical record
            virtual_data_sources = {"historical_record": record}
            
            # Use extract_field for each standardized field
            standardized_record = {
                "year": self.extract_field("year", virtual_data_sources),
                "tax_levied": self.extract_field("tax_levied", virtual_data_sources),
                "tax_paid": self.extract_field("tax_paid", virtual_data_sources),
                "date_paid": self.extract_field("date_paid", virtual_data_sources),
                "amount_due": self.extract_field("amount_due", virtual_data_sources),
                "first_half": {
                    "tax_levied": self.extract_field("first_half_tax_levied", virtual_data_sources),
                    "tax_paid": self.extract_field("first_half_tax_paid", virtual_data_sources),
                    "date_paid": self.extract_field("first_half_date_paid", virtual_data_sources),
                    "amount_due": self.extract_field("first_half_amount_due", virtual_data_sources)
                },
                "second_half": {
                    "tax_levied": self.extract_field("second_half_tax_levied", virtual_data_sources),
                    "tax_paid": self.extract_field("second_half_tax_paid", virtual_data_sources),
                    "date_paid": self.extract_field("second_half_date_paid", virtual_data_sources),
                    "amount_due": self.extract_field("second_half_amount_due", virtual_data_sources)
                }
            }
            
            # Only add if we got at least a year
            if standardized_record["year"]:
                standardized_historical.append(standardized_record)
        
        return standardized_historical
    
    def standardize_tax_data(self) -> Dict:
        """Standardize tax data from any scraper into consistent format."""
        print(f"[TAX] Standardizing tax data for county: {self.county}")
        
        raw_tax_data = self.raw_data.get("tax_data") if self.raw_data else None
        
        if not raw_tax_data or raw_tax_data.get("error"):
            return {
                "status": "error",
                "message": raw_tax_data.get("error", "Tax data unavailable") if raw_tax_data else "Tax data unavailable",
                "data": None,
                "source": raw_tax_data.get("source", f"tax_scraper_{self.county}"),
                "timestamp": datetime.now().isoformat()
            }
        
        # Create data sources dict for config-driven extraction
        data_sources = {
            "tax_data": raw_tax_data,
            "property_data": self.raw_data.get("property_data") if self.raw_data else None,
            "clerk_data": self.raw_data.get("clerk_data") if self.raw_data else None
        }
        
        # Extract common fields using config - now uses self.county
        standardized = {
            "status": "success",
            "message": "Tax data retrieved successfully",
            "data": {
                "county": self.county.replace("_", " ").title(),
                "tax_id": self.extract_field("tax_id", data_sources),
                "tax_year": self.extract_field("tax_year", data_sources),
                "assessed_value": self.extract_field("assessed_value", data_sources),
                "taxable_value": self.extract_field("taxable_value", data_sources),
                "tax_amount": self.extract_field("tax_amount", data_sources),
                "first_half_due_date": self.extract_field("first_half_due_date", data_sources),
                "second_half_due_date": self.extract_field("second_half_due_date", data_sources),
                "status": self.extract_field("status", data_sources),
                "tax_district": self.extract_field("tax_district", data_sources),
                "mill_levy": self.extract_field("mill_levy", data_sources),
                "account_number": self.extract_field("account_number", data_sources),
                "owner_name": self.extract_field("owner_name", data_sources),
                "property_address": self.extract_field("property_address", data_sources),
                # Current year tax data fields - now using config-driven extraction
                "total_tax_levied": self.extract_field("total_tax_levied", data_sources),
                "tax_received": self.extract_field("tax_received", data_sources),
                "amount_due": self.extract_field("amount_due", data_sources),
                "first_half_levied": self.extract_field("first_half_levied", data_sources),
                "first_half_paid": self.extract_field("first_half_paid", data_sources),
                "second_half_levied": self.extract_field("second_half_levied", data_sources),
                "second_half_paid": self.extract_field("second_half_paid", data_sources),
                "historical_data": self.extract_field("historical_data", data_sources)
            },
            "source": raw_tax_data.get("source", f"tax_scraper_{self.county}"),
            "timestamp": datetime.now().isoformat()
        }
        
        return standardized
    
    def standardize_property_data(self,) -> Dict:
        """Standardize property details data from any scraper into consistent format."""
        raw_property_data = self.raw_data.get("property_data") if self.raw_data else None
        
        if not raw_property_data or raw_property_data.get("error"):
            return {
                "status": "error",
                "message": raw_property_data.get("error", "Property data unavailable") if raw_property_data else "Property data unavailable",
                "data": None,
                "source": raw_property_data.get("source", f"property_scraper_{self.county}") if raw_property_data else f"property_scraper_{self.county}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Create data sources dict for config-driven extraction
        data_sources = {
            "tax_data": self.raw_data.get("tax_data") if self.raw_data else None,
            "property_data": raw_property_data,
            "clerk_data": self.raw_data.get("clerk_data") if self.raw_data else None
        }
        
        standardized = {
            "status": "success",
            "message": "Property data retrieved successfully",
            "data": {
                "county": self.county.replace("_", " ").title(),
                "county_parcel_id": self.extract_field("county_parcel_id", data_sources),
                "tax_id": self.extract_field("tax_id", data_sources),
                "physical_address": self.extract_field("physical_address", data_sources),
                "mailing_address": self.extract_field("mailing_address", data_sources),
                "owner_name": self.extract_field("owner_name", data_sources),
                "legal_description": self.extract_field("legal_description", data_sources),
                "total_property_value": self.extract_field("total_property_value", data_sources),
                "land_value": self.extract_field("land_value", data_sources),
                "developments_value": self.extract_field("developments_value", data_sources),
                "total_acreage": self.extract_field("total_acreage", data_sources),
                "acreage_breakdown": self.extract_field("acreage_breakdown", data_sources),
                "num_developments": self.extract_field("num_developments", data_sources),
                "developments": self.extract_field("developments", data_sources)
            },
            "source": raw_property_data.get("source", f"property_scraper_{self.county}"),
            "timestamp": datetime.now().isoformat()
        }
        
        return standardized
    
    def standardize_clerk_data(self) -> Dict:
        """Standardize clerk/recorder data into consistent format."""
        raw_clerk_data = self.raw_data.get("clerk_data") if self.raw_data else None
        
        if not raw_clerk_data or raw_clerk_data.get("error"):
            return {
                "status": "error",
                "message": raw_clerk_data.get("error", "Clerk data unavailable") if raw_clerk_data else "Clerk data unavailable",
                "data": None,
                "source": raw_clerk_data.get("source", f"clerk_scraper_{self.county}") if raw_clerk_data else f"clerk_scraper_{self.county}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Create data sources dict for config-driven extraction
        data_sources = {
            "tax_data": self.raw_data.get("tax_data") if self.raw_data else None,
            "property_data": self.raw_data.get("property_data") if self.raw_data else None,
            "clerk_data": raw_clerk_data
        }
        
        standardized = {
            "status": "success",
            "message": "Clerk data retrieved successfully",
            "data": {
                "county": self.county.replace("_", " ").title(),
                "deeds": self.extract_field("deeds", data_sources),
                "mortgages": self.extract_field("mortgages", data_sources),
                "liens": self.extract_field("liens", data_sources)
            },
            "source": raw_clerk_data.get("source", f"clerk_scraper_{self.county}"),
            "timestamp": datetime.now().isoformat()
        }
        
        return standardized
    
    def _create_general_info(self) -> Dict:
        """Create general info section from available data sources."""
        
        # Create data sources dict for config-driven extraction
        data_sources = {
            "tax_data": self.raw_data.get("tax_data") if self.raw_data else None,
            "property_data": self.raw_data.get("property_data") if self.raw_data else None,
            "clerk_data": self.raw_data.get("clerk_data") if self.raw_data else None
        }
        
        # Extract all general info fields using config
        general_info = {
            "county_state": self.extract_field("county_state", data_sources),
            "owner_name": self.extract_field("owner_name", data_sources),
            "physical_address": self.extract_field("physical_address", data_sources),
            "mailing_address": self.extract_field("mailing_address", data_sources),
            "county_parcel_id": self.extract_field("county_parcel_id", data_sources),
            "tax_id": self.extract_field("tax_id", data_sources),
            "account_number": self.extract_field("account_number", data_sources),
            "acres": self.extract_field("acres", data_sources)
        }
        
        return general_info
    
    def _count_developments(self, developments: List[Dict]) -> int:
        """Count the number of developments."""
        if not developments:
            return 0
        return len(developments)
    
    def _standardize_developments(self, developments: List[Dict]) -> List[Dict]:
        """Standardize each development in the developments array."""
        if not developments:
            return []
        
        standardized_developments = []
        for development in developments:
            # Skip components - only process main buildings
            print("development.get(Component Type): ", development.get("Component Type"))
            if development.get("Component Type") == "Component":
                print(f"[DEBUG] Skipping component: {development.get('Building Component', 'Unknown Component')}")
                continue
            
            # Create virtual data source for this single development
            virtual_data_sources = {"development": development}
            
            standardized_dev = {}
            # Use extract_field for each standardized field - now uses self.county
            standardized_dev["id"] = self.extract_field("id", virtual_data_sources)
            standardized_dev["description"] = self.extract_field("description", virtual_data_sources)
            standardized_dev["stories"] = self.extract_field("stories", virtual_data_sources)
            standardized_dev["sq_ft"] = self.extract_field("sq_ft", virtual_data_sources)
            standardized_dev["exterior"] = self.extract_field("exterior", virtual_data_sources)
            standardized_dev["roof_cover"] = self.extract_field("roof_cover", virtual_data_sources)
            standardized_dev["bedrooms"] = self.extract_field("bedrooms", virtual_data_sources)
            standardized_dev["year_built"] = self.extract_field("year_built", virtual_data_sources)
            
            standardized_developments.append(standardized_dev)
        
        return standardized_developments
    
    def _format_acreage_breakdown(self, acreage_data: Dict) -> Dict:
        """Convert acreage breakdown dict to standardized JSON format."""
        if not acreage_data:
            return {}
        
        # Define standard acreage categories
        standard_categories = ["residential", "agricultural", "commercial", "industrial", "other"]
        
        breakdown = {}
        for category in standard_categories:
            # Get acres from data, default to 0 if category not present
            acres = acreage_data.get(category, 0)
            breakdown[category] = acres
        
        return breakdown
    
    @staticmethod
    def standardize_api_response(tax_data: Optional[Dict], property_data: Optional[Dict], 
                           clerk_data: Optional[Dict], county: str, county_links: Dict = None) -> Dict:
        """Standardize the complete API response."""
        
        # Create raw data structure
        raw_data = {
            "tax_data": tax_data,
            "property_data": property_data,
            "clerk_data": clerk_data,
            "county_links": county_links  # Add links to raw data
        }
        print(f"[DEBUG] Raw data: {county}")
        # Create standardizer instance with raw data AND county
        standardizer = DataStandardizer(raw_data=raw_data, county=county)
        
        # Create general info from available data sources
        general_info = standardizer._create_general_info()
        
        # Add county links to general info
        if county_links:
            general_info["county_links"] = {
                "tax_records": county_links.get("tax_field"),
                "property_details": county_links.get("property_details_field"), 
                "clerk_records": county_links.get("clerk_field")
            }
        
        return {
            "status": "success",
            "message": "Property information retrieved successfully",
            "data": {
                "general_info": general_info,
                "tax": standardizer.standardize_tax_data(),
                "property_details": standardizer.standardize_property_data(),
                "clerk": standardizer.standardize_clerk_data()
            },
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "available_sections": [
                    section for section in [
                        "general_info",
                        "tax" if tax_data and not tax_data.get("error") else None,
                        "property_details" if property_data and not property_data.get("error") else None,
                        "clerk" if clerk_data and not clerk_data.get("error") else None
                    ]
                ]
            }
        }
    
   