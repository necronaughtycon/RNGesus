import asyncio
import asyncpg
import logging
from config import DATABASE_URL

logger = logging.getLogger('discord_bot')
db_pool = None

async def get_db_pool():
    global db_pool
    return db_pool

async def setup_database(bot):
    global db_pool
    try:
        # Connection with retry logic
        retry_attempts = 5
        retry_delay = 5  # seconds
        
        for attempt in range(retry_attempts):
            try:
                db_pool = await asyncpg.create_pool(DATABASE_URL)
                logger.info("Successfully connected to database")
                
                # Ensure tables exist
                await create_tables()
                
                # Attach pool to bot for easy access
                bot.db_pool = db_pool
                return True
            except Exception as e:
                if attempt < retry_attempts - 1:
                    logger.warning(f"Database connection attempt {attempt+1} failed: {e}. Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    logger.error(f"All database connection attempts failed: {e}")
                    return False
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}")
        return False

async def create_tables():
    """Create necessary tables if they don't exist"""
    global db_pool
    async with db_pool.acquire() as conn:
        # Create button_messages table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS button_messages (
                button_id TEXT PRIMARY KEY,
                channel_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL
            )
        ''')
        
        # Create rolls table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rolls (
                id SERIAL PRIMARY KEY,
                button_id TEXT NOT NULL,
                user_id BIGINT NOT NULL,
                user_display_name TEXT NOT NULL,
                roll INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(button_id, user_id)
            )
        ''')