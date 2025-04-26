import asyncio
import datetime
import logging

logger = logging.getLogger('discord_bot')

class RateLimiter:
    def __init__(self, max_operations_per_second, reset_time=1):
        self.max_operations = max_operations_per_second
        self.reset_time = reset_time  # in seconds
        self.operations_count = 0
        self.last_reset = datetime.datetime.now()
        self.total_operations = 0  # for tracking total usage
    
    async def acquire(self):
        current_time = datetime.datetime.now()
        time_diff = (current_time - self.last_reset).total_seconds()
        
        # Reset counter if reset_time has passed
        if time_diff >= self.reset_time:
            self.operations_count = 0
            self.last_reset = current_time
        
        # Check if we're at the limit
        if self.operations_count >= self.max_operations:
            # Calculate wait time
            wait_time = self.reset_time - time_diff
            if wait_time > 0:
                logger.warning(f"Rate limit throttling. Waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                # Recursive call after waiting
                return await self.acquire()
        
        # Increment counter and allow operation
        self.operations_count += 1
        self.total_operations += 1
        return True
    
    def get_usage_stats(self):
        return {
            "current_window": self.operations_count,
            "max_per_window": self.max_operations,
            "total_since_startup": self.total_operations
        }

# Create a global rate limiter instance
from config import MAX_OPERATIONS_PER_SECOND, RATE_LIMIT_RESET_TIME
rate_limiter = RateLimiter(MAX_OPERATIONS_PER_SECOND, RATE_LIMIT_RESET_TIME)

async def handle_api_error(error):
    """Handle Discord API errors, particularly rate limiting"""
    import discord
    
    if isinstance(error, discord.errors.HTTPException):
        if error.status == 429:  # Too Many Requests
            retry_after = error.retry_after if hasattr(error, 'retry_after') else 60
            logger.warning(f"Rate limited by Discord. Waiting {retry_after} seconds")
            await asyncio.sleep(retry_after)
            return True  # Signal that we should retry
    return False  # Don't retry for other errors