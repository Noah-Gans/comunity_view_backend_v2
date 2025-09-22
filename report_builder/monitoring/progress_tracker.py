"""Progress tracker for monitoring collection progress"""

import time
from datetime import datetime, timedelta

class ProgressTracker:
    """Tracks progress of mass data collection"""
    
    def __init__(self):
        self.total_parcels = 0
        self.completed_parcels = 0
        self.failed_parcels = 0
        self.start_time = None
        self.last_update_time = None
        
    def initialize(self, total_parcels: int):
        """Initialize the tracker with total parcel count"""
        self.total_parcels = total_parcels
        self.completed_parcels = 0
        self.failed_parcels = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        
        print(f"Progress Tracker initialized: {total_parcels} total parcels")
        
    def increment_completed(self):
        """Increment completed parcel count"""
        self.completed_parcels += 1
        self._maybe_print_progress()
        
    def increment_failed(self):
        """Increment failed parcel count"""
        self.failed_parcels += 1
        self._maybe_print_progress()
        
    def _maybe_print_progress(self):
        """Print progress update if enough time has passed"""
        current_time = time.time()
        
        # Print update every 30 seconds
        if current_time - self.last_update_time >= 30:
            self.print_progress()
            self.last_update_time = current_time
    
    def print_progress(self):
        """Print current progress"""
        if self.start_time is None:
            return
            
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        total_processed = self.completed_parcels + self.failed_parcels
        
        if total_processed == 0:
            return
            
        # Calculate rates and estimates
        rate_per_second = total_processed / elapsed_time
        rate_per_minute = rate_per_second * 60
        
        remaining_parcels = self.total_parcels - total_processed
        eta_seconds = remaining_parcels / rate_per_second if rate_per_second > 0 else 0
        eta_time = datetime.now() + timedelta(seconds=eta_seconds)
        
        # Calculate percentage
        percentage = (total_processed / self.total_parcels) * 100
        
        print(f"\n=== PROGRESS UPDATE ===")
        print(f"Completed: {self.completed_parcels}")
        print(f"Failed: {self.failed_parcels}")
        print(f"Total Processed: {total_processed}/{self.total_parcels} ({percentage:.1f}%)")
        print(f"Rate: {rate_per_minute:.1f} parcels/minute")
        print(f"Elapsed: {elapsed_time/3600:.1f} hours")
        print(f"ETA: {eta_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"========================\n")
        
    def print_final_summary(self):
        """Print final collection summary"""
        total_time = time.time() - self.start_time
        total_processed = self.completed_parcels + self.failed_parcels
        
        print(f"\n=== COLLECTION COMPLETE ===")
        print(f"Total Parcels: {self.total_parcels}")
        print(f"Completed Successfully: {self.completed_parcels}")
        print(f"Failed: {self.failed_parcels}")
        
        # Fix division by zero
        if total_processed > 0:
            print(f"Success Rate: {(self.completed_parcels/total_processed)*100:.1f}%")
            print(f"Total Time: {total_time/3600:.1f} hours")
            print(f"Average Rate: {(total_processed/(total_time/60)):.1f} parcels/minute")
        else:
            print(f"Success Rate: N/A (no parcels processed)")
            print(f"Total Time: {total_time/3600:.1f} hours")
            print(f"Average Rate: 0 parcels/minute")
        
        print(f"============================\n")
