import logging
from discord.ext import tasks
from utils.rate_limiter import rate_limiter

logger = logging.getLogger('discord_bot')

# Monitor rate limits task
@tasks.loop(seconds=15)
async def monitor_rate_limits():
    global rate_limiter
    stats = rate_limiter.get_usage_stats()
    
    # Only log if there's been activity
    if stats["total_since_startup"] > 0:
        # Log detailed stats every minute (approximately)
        if monitor_rate_limits.current_loop % 4 == 0:
            logger.info(f"API usage: {stats['current_window']}/{stats['max_per_window']} requests in current window, " +
                      f"{stats['total_since_startup']} total since startup")
        
        # If we're hitting near capacity frequently, log a warning
        if stats["current_window"] >= stats["max_per_window"] * 0.9:
            logger.warning(f"High API usage detected: {stats['current_window']}/{stats['max_per_window']} " +
                          f"({stats['current_window']/stats['max_per_window']*100:.1f}%)")

# Background task for database connection health checks
@tasks.loop(minutes=5)
async def check_db_connection():
    # Import here to avoid circular imports
    from db.connection import get_db_pool
    
    db_pool = await get_db_pool()
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
            logger.info("Database connection check: OK")
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")

async def start_background_tasks(bot):
    # Attach tasks to bot for reference
    bot.monitor_task = monitor_rate_limits
    bot.db_check_task = check_db_connection
    
    # Start background tasks
    monitor_rate_limits.start()
    check_db_connection.start()
    
    return True