import discord
import pytz
import logging
from config import AUTHORIZED_ADMIN_IDS
from utils.rate_limiter import rate_limiter

logger = logging.getLogger('discord_bot')

class ConfirmDeleteButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Confirm Delete", style=discord.ButtonStyle.danger)
    
    async def callback(self, interaction: discord.Interaction):
        parent_view = self.view
        
        # Change the message to indicate deletion in progress
        await interaction.response.edit_message(content="Deleting...", view=None)
        
        # Perform the deletion
        success = await perform_delete(
            interaction, 
            parent_view.button_id,
            parent_view.roll_being_deleted['user_id'],
            parent_view.roll_being_deleted['username']
        )
        
        # Update the SAME ephemeral message with the result
        if success:
            await interaction.edit_original_response(
                content=f"✅ Deleted roll for **{parent_view.roll_being_deleted['username']}**"
            )
            # No auto-disappear, admin must dismiss manually
        else:
            await interaction.edit_original_response(
                content="⚠️ Failed to delete the roll."
            )


class CancelDeleteButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.secondary)
    
    async def callback(self, interaction: discord.Interaction):
        # Just close the message
        await interaction.response.edit_message(content="Operation cancelled.", view=None)


class DeleteRollButton(discord.ui.Button):
    def __init__(self, parent_view, button_id, user_id, username, row_number):
        self.parent_view = parent_view
        self.button_id = button_id
        self.user_id = user_id
        self.username = username
        super().__init__(
            label=f"🗑️ {username}", 
            style=discord.ButtonStyle.danger, 
            custom_id=f"delete_{user_id}", 
            row=row_number
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id not in AUTHORIZED_ADMIN_IDS:
            await interaction.response.send_message("⛔ You're not authorized to delete rolls.", ephemeral=True)
            return
        
        # Show confirmation in the same view
        roll_info = {
            'user_id': self.user_id,
            'username': self.username
        }
        await self.parent_view.show_delete_confirmation(interaction, roll_info)


class AdminRollManager(discord.ui.View):
    def __init__(self, button_id, rolls):
        super().__init__(timeout=180)
        self.button_id = button_id
        self.in_delete_confirmation_mode = False
        self.roll_being_deleted = None
        
        # Add delete buttons for each roll
        for i, roll in enumerate(rolls):
            row_num = i % 5  # Up to 5 rows
            delete_button = DeleteRollButton(
                self, button_id, roll["user_id"], 
                roll["user_display_name"], row_number=row_num
            )
            self.add_item(delete_button)
    
    # New method to switch to confirmation mode
    async def show_delete_confirmation(self, interaction, roll_info):
        self.in_delete_confirmation_mode = True
        self.roll_being_deleted = roll_info
        
        # Clear existing buttons
        self.clear_items()
        
        # Add confirm and cancel buttons
        self.add_item(ConfirmDeleteButton())
        self.add_item(CancelDeleteButton())
        
        # Update the message with confirmation text
        await interaction.response.edit_message(
            content=f"⚠️ Are you sure you want to delete the roll for **{roll_info['username']}**?",
            view=self
        )


async def perform_delete(interaction, button_id, user_id, username):
    # Import here to avoid circular imports
    from db.operations import delete_roll, get_message_info, get_rolls
    
    try:
        # Step 1: Delete from DB
        await delete_roll(button_id, user_id)

        # Step 2: Get message and channel IDs
        msg_row = await get_message_info(button_id)
        if not msg_row:
            return False

        channel_id = msg_row["channel_id"]
        message_id = msg_row["message_id"]

        # Step 3: Fetch updated roll list
        updated_rolls = []
        results = await get_rolls(button_id)
        for r in results:
            updated_rolls.append({
                "user_display_name": r["user_display_name"],
                "roll": r["roll"],
                "timestamp": r["timestamp"]
            })

        # Step 4: Regenerate public roll message
        if updated_rolls:
            est = pytz.timezone("US/Eastern")
            highest = max(updated_rolls, key=lambda r: r["roll"])
            lowest = min(updated_rolls, key=lambda r: r["roll"])

            result_lines = []
            for r in updated_rolls:
                name, value, timestamp = r["user_display_name"], r["roll"], r["timestamp"]
                emoji = (
                    "👑" if (name, value) == (highest["user_display_name"], highest["roll"]) else
                    "💀" if (name, value) == (lowest["user_display_name"], lowest["roll"]) and len(updated_rolls) > 1 else
                    "🎲"
                )
                result_lines.append(f"{emoji} **{name}** rolled **{value}**")
            new_content = "\n".join(result_lines)
        else:
            new_content = "🎲 No rolls yet. Be the first to click!"

        # Import here to avoid circular imports
        from ui.roll_button import RollButton
        
        # Step 5: Edit original roll message - with rate limiting
        await rate_limiter.acquire()
        channel = await interaction.client.fetch_channel(channel_id)
        if not channel:
            return False

        await rate_limiter.acquire()
        msg = await channel.fetch_message(message_id)
        view = RollButton(button_id=button_id)
        await rate_limiter.acquire()
        await msg.edit(content=new_content, view=view)
        
        return True
        
    except Exception as e:
        logger.error(f"Delete operation failed: {e}")
        return False