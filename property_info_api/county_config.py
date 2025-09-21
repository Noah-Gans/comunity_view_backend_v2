"""County-specific configuration for link construction."""

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
    print(f"[CONFIG] Constructing links for county: {county}")
    print(f"[CONFIG] Fields: {fields}")
    
    county_config = COUNTY_CONFIG.get(county, {})
    print(f"[CONFIG] Found config: {county_config}")
    
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
        print(f"[CONFIG] Link config for {field_name}: {link_config}")
        
        if "static_url" in link_config:
            # Static URL (like clerk records that don't need field values)
            links[field_name] = link_config["static_url"]
        elif field_value and "base_url" in link_config and "field" in link_config:
            # Dynamic URL that needs field value (only process if field_value exists)
            base_url = link_config["base_url"]
            links[field_name] = f"{base_url}{field_value}"
    
    print(f"[CONFIG] Final links: {links}")
    return links
