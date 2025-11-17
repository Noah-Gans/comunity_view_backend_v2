#!/usr/bin/env python3
"""
Start multiple FastAPI instances for load balancing
"""
import subprocess
import time
import signal
import sys
import os

def start_instances():
    """Start multiple FastAPI instances for load balancing"""
    processes = []
    ports = [9011, 9012, 9013]  # Three instances - avoiding 9000-9003 (other services)
    
    # Navigate to property_api directory from scripts/vm1_services/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    property_api_dir = os.path.join(project_root, 'services', 'property_api')
    os.chdir(property_api_dir)
    
    try:
        for port in ports:
            print(f"Starting FastAPI instance on port {port}")
            process = subprocess.Popen([
                "uvicorn", "main:app",  # Back to main:app since we're in the directory
                "--host", "0.0.0.0", 
                "--port", str(port),
                "--log-level", "info"
            ], env={**os.environ, 'PYTHONPATH': os.path.dirname(script_dir), 'INSTANCE_PORT': str(port)})  # Add port as env var
            processes.append(process)
            time.sleep(2)  # Give each instance time to start
        
        print(f"Started {len(processes)} FastAPI instances")
        print("Press Ctrl+C to stop all instances")
        
        # Wait for all processes
        for process in processes:
            process.wait()
            
    except KeyboardInterrupt:
        print("\nStopping all instances...")
        for process in processes:
            process.terminate()
        print("All instances stopped")

if __name__ == "__main__":
    start_instances()
