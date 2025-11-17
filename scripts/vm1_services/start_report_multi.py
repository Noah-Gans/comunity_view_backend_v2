#!/usr/bin/env python3
"""
Start multiple Report API instances for load balancing
"""
import subprocess
import time
import signal
import sys
import os

def start_instances():
    """Start multiple Report API instances for load balancing"""
    processes = []
    ports = [9021, 9022, 9023]  # Three instances - avoiding 9000-9003 (other services) and 9011-9013 (property API)
    
    # Navigate to report_api directory from scripts/vm1_services/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    report_api_dir = os.path.join(project_root, 'services', 'report_api')
    os.chdir(report_api_dir)
    
    try:
        for port in ports:
            print(f"Starting Report API instance on port {port}")
            process = subprocess.Popen([
                "uvicorn", "app:app",  # Use uvicorn directly with app:app
                "--host", "0.0.0.0",
                "--port", str(port),
                "--log-level", "info"
            ], env={**os.environ, 'PYTHONPATH': project_root, 'PORT': str(port), 'INSTANCE_PORT': str(port)})
            processes.append(process)
            time.sleep(2)  # Give each instance time to start
        
        print(f"Started {len(processes)} Report API instances on ports {ports}")
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

