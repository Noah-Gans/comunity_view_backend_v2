#!/usr/bin/env python3
"""
Simple startup script for the Property Search API
"""

import uvicorn
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_api.app import app

if __name__ == "__main__":
    print("🚀 Starting Property Search API...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 