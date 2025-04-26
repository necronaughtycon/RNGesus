import discord
from discord import app_commands
from utils.rate_limiter import rate_limiter
import logging

logger = logging.getLogger('discord_bot')

def register_commands(bot):
    @bot.tree.command(name="rollbutton", description="Post a roll button")
    async def rollbutton(interaction: discord.Interaction):
        # Import here to avoid circular imports
        from ui.roll_button import RollButton
        from db.operations import save_button_message
        
        view = RollButton()
        
        # Apply rate limiting before sending
        await rate_limiter.acquire()
        await interaction.response.send_message("🎲 Click the button to roll!", view=view)
        message = await interaction.original_response()

        await save_button_message(view.button_id, interaction.channel.id, message.id)