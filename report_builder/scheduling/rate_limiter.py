"""Rate limiter for controlling request frequency"""

import asyncio
import random
import time

class RateLimiter:
    """Rate limiter to control scraping frequency"""
    
    def __init__(self, requests_per_second: float = 1.2):
        self.requests_per_second = requests_per_second
        self.min_delay = 1.0 / requests_per_second
        self.last_request_time = 0
        
    async def wait(self):
        """Wait for appropriate delay before next request"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Calculate delay needed
        base_delay = self.min_delay
        random_jitter = random.uniform(0.8, 1.2)  # Add randomness
        required_delay = base_delay * random_jitter
        
        # If we need to wait more, do so
        if time_since_last < required_delay:
            sleep_time = required_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
