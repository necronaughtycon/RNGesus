import discord
import logging
from utils.rate_limiter import rate_limiter

logger = logging.getLogger('discord_bot')

def register_events(bot):
    # Import here to avoid circular imports
    from handlers.commands import register_commands
    
    # Register commands
    register_commands(bot)
    
    @bot.event
    async def on_ready():
        logger.info(f"Logged in as {bot.user}")
        try:
            await bot.tree.sync()
            logger.info("Synced slash commands")
        except Exception as e:
            logger.error(f"Slash sync failed: {e}")

        try:
            # Import here to avoid circular imports
            from db.operations import get_button_messages
            from ui.roll_button import RollButton
            
            # Rate limit this operation
            await rate_limiter.acquire()
            rows = await get_button_messages()

            for row in rows:
                # Apply rate limiting for each fetch and edit
                await rate_limiter.acquire()
                channel = bot.get_channel(row["channel_id"])
                if channel:
                    try:
                        await rate_limiter.acquire()
                        msg = await channel.fetch_message(row["message_id"])
                        view = RollButton(button_id=row["button_id"])
                        
                        await rate_limiter.acquire()
                        await msg.edit(view=view)
                        logger.info(f"Restored view on message {msg.id}")
                    except discord.NotFound:
                        logger.warning(f"Message {row['message_id']} not found - may have been deleted")
                    except discord.Forbidden:
                        logger.warning(f"Forbidden to access message {row['message_id']}")
                    except Exception as e:
                        logger.warning(f"Failed to restore message {row['message_id']}: {e}")
        except Exception as e:
            logger.error(f"View restore error: {e}")

    @bot.event
    async def on_error(event, *args, **kwargs):
        logger.error(f"Event error in {event}: {args} {kwargs}")

    @bot.event 
    async def on_command_error(ctx, error):
        if isinstance(error, discord.ext.commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        else:
            logger.error(f"Command error: {error}")