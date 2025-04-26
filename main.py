import asyncio
import logging
from config import BOT_TOKEN
from db.connection import setup_database
from tasks.background import start_background_tasks
import discord
from discord.ext import commands

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discord_bot')

# Configure intents
intents = discord.Intents.default()
intents.members = True

# Configure bot
bot = commands.Bot(command_prefix="/", intents=intents)

async def init_bot():
    # Setup database
    success = await setup_database(bot)
    if not success:
        return False
    
    # Register events (import here to avoid circular imports)
    from handlers.events import register_events
    register_events(bot)
    
    # Start background tasks
    await start_background_tasks(bot)
    
    return True

def main():
    @bot.event
    async def setup_hook():
        success = await init_bot()
        if not success:
            logger.critical("Failed to initialize bot")
            await bot.close()
    
    try:
        bot.run(BOT_TOKEN)
    except discord.errors.LoginFailure:
        logger.critical("Invalid token provided")
    except discord.errors.HTTPException as e:
        if e.status == 429:
            logger.critical("Rate limited during login. Wait a while before trying again.")
        else:
            logger.critical(f"HTTP Exception: {e}")
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()