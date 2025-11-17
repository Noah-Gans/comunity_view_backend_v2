#!/usr/bin/env python3
"""
Simple startup script for the Property Search API
"""

import uvicorn
import sys
import os

# Navigate to project root and add to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

# Change to search_api directory
search_api_dir = os.path.join(project_root, 'services', 'search_api')
os.chdir(search_api_dir)

# Now import app
from app import app

if __name__ == "__main__":
    print("🚀 Starting Property Search API...")
    print(f"📁 Working directory: {os.getcwd()}")
    uvicorn.run(app, host="0.0.0.0", port=9001) 