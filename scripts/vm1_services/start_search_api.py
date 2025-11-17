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
    # Navigate to search_api directory from scripts/vm1_services/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    search_api_dir = os.path.join(project_root, 'services', 'search_api')
    os.chdir(search_api_dir)
    
    print("🚀 Starting Property Search API...")
    print(f"📁 Working directory: {os.getcwd()}")
    uvicorn.run("app:app", host="0.0.0.0", port=9001) 