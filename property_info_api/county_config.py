"""County-specific configuration for link construction."""
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

COUNTY_CONFIG = {
    "teton_county_wy": {
        "tax_details": {
            "base_url": "https://gis.tetoncountywy.gov/portal/apps/dashboards/5574848e46464109a14dead33e5ddace#ParcelInfo=",
            "field": "tax_id"
        },
        "property_details": {
            "base_url": "https://gis.tetoncountywy.gov/portal/apps/dashboards/ca93f7b7ae3e4d51ad371121a64ee739#accountno=",
            "field": "accountno"
        },
        "clerk_records": {
            # Dashboard URL for frontend display
            "base_url": "https://gis.tetoncountywy.gov/portal/apps/dashboards/03ef10d8b8634909b6263e9016bcc986#statepin=",
            "field": "pidn"
        }
    },
    "lincoln_county_wy": {
        "tax_details": {
            "base_url": "https://itax.tylertech.com/LincolnWY/detail.aspx?taxid=",
            "field": "RWACCT"
        },
        "property_details": {
            "base_url": "https://propertydetails.lcwy.org/Home/Detail/",
            "field": "RWACCT"
        },
        "clerk_records": {
            "static_url": "https://idocmarket.com/Subscription/Subscribe?county=LINWY1"
        }
    },
    "sublette_county_wy": {
        "tax_details": {
            "base_url": "https://maps.terragis.net/sublette/treas/query/search.php?Tax_ID=",
            "field": "tax_id"
        },
        "property_details": {
            "base_url": "https://maps.terragis.net/sublette/mapserver/tabDetail.php?v=2&accountno=",
            "field": "accountno"
        },
        "clerk_records": {
            "base_url": "https://maps.terragis.net/sublette/clerk/query/list.php?pidn=",
            "field": "pidn"
        }
    },
    "fremont_county_wy": {
        "tax_details": {
            "base_url": "https://itax.tylertech.com/FremontWY/detail.aspx?taxid=",
            "field": "tax_id"
        },
        "property_details": {
            "base_url": "https://maps.terragis.net/fremontwy/tabDetail.php?v=2&accountno=",
            "field": "accountno"
        },
        "clerk_records": {
            "static_url": "https://fremontcountywy-recorder.tylerhost.net/recorder/eagleweb/docSearch.jsp"
        }
    }
}

def construct_links(county: str, fields: dict) -> dict:
    """Construct URLs for all data types based on county and field values."""
    logger.info(f"(County Config) Building links for {county}")
    
    county_config = COUNTY_CONFIG.get(county, {})
    if not county_config:
        logger.warning(f"(County Config) No config found for county: {county}")
        return {}
    
    links = {}
    
    # Map field names to config keys
    field_mapping = {
        "tax_field": "tax_details",
        "property_details_field": "property_details", 
        "clerk_field": "clerk_records"
    }
    
    for field_name, field_value in fields.items():
        config_key = field_mapping.get(field_name)
        if not config_key:
            continue
            
        link_config = county_config.get(config_key, {})
        
        if "static_url" in link_config:
            # Static URL (like clerk records that don't need field values)
            links[field_name] = link_config["static_url"]
        elif field_value and "url_template" in link_config and "field" in link_config:
            links[field_name] = link_config["url_template"].format(value=field_value)
        elif field_value and "base_url" in link_config and "field" in link_config:
            # Dynamic URL that needs field value (only process if field_value exists)
            base_url = link_config["base_url"]
            links[field_name] = f"{base_url}{field_value}"
    
    logger.info(f"(County Config) Built {len(links)} links for {county}")
    return links
