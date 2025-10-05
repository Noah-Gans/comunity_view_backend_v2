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
    """Start multiple FastAPI instances"""
    processes = []
    ports = [8001, 8002, 8003]  # Three instances
    
    # Change to the property_info_api directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        for port in ports:
            print(f"Starting FastAPI instance on port {port}")
            process = subprocess.Popen([
                "uvicorn", "main:app", 
                "--host", "0.0.0.0", 
                "--port", str(port),
                "--log-level", "info"
            ])
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
