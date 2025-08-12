"""Configuration settings for the property info API."""

import os
from pathlib import Path

# Environment detection
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Database paths
if ENVIRONMENT == 'production':
    # Production paths (VM)
    TETON_IDAHO_DB_PATH = "/opt/teton_gis/teton_county_id.db"
    TETON_IDAHO_DATA_DIR = "/opt/teton_gis/data"
    TETON_IDAHO_PROCESSED_DIR = "/opt/teton_gis/processed"
else:
    # Development paths (local)
    TETON_IDAHO_DB_PATH = Path(__file__).parent / "teton_county_id_download" / "processed" / "teton_county_id.db"
    TETON_IDAHO_DATA_DIR = Path(__file__).parent / "teton_county_id_download" / "data"
    TETON_IDAHO_PROCESSED_DIR = Path(__file__).parent / "teton_county_id_download" / "processed"

# Override mappings for different domains
OVERRIDE_MAP = {
    "tetoncountywy.gov": {
        "tax": "overrides.teton.scrape_tax",
        "clerk": "overrides.teton.scrape_clerk"
    }
}

# API settings
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 8000))
API_WORKERS = int(os.getenv('API_WORKERS', 1))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s' 