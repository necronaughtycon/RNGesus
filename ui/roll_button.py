import uuid
import random
import discord
import pytz
from config import AUTHORIZED_ADMIN_IDS
from utils.rate_limiter import rate_limiter

class RollButton(discord.ui.View):
    def __init__(self, button_id=None):
        super().__init__(timeout=None)
        self.button_id = button_id or uuid.uuid4()

    def is_authorized(self, user_id):
        return user_id in AUTHORIZED_ADMIN_IDS

    @discord.ui.button(label="🎲 CLICK HERE TO ROLL! 🎲", style=discord.ButtonStyle.primary, custom_id="roll_button", row=0)
    async def roll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Import here to avoid circular imports
        from db.operations import has_user_rolled, save_roll, get_rolls
        
        user_id = interaction.user.id
        user_display_name = interaction.user.display_name

        if await has_user_rolled(self.button_id, user_id):
            await interaction.response.send_message("‼️ You've already rolled on this item ‼️", ephemeral=True)
            return

        roll = random.randint(1, 100)
        await save_roll(self.button_id, user_id, user_display_name, roll)

        # Apply rate limiting for fetch
        await rate_limiter.acquire()
        results = await get_rolls(self.button_id)
        rolls = [(r["user_display_name"], r["roll"], r["timestamp"]) for r in results]

        # Determine highest and lowest roll values
        values = [value for _, value, _ in rolls]
        highest_value = max(values)
        lowest_value = min(values)

        # Check for tie at the highest roll
        top_rollers = [(name, value) for name, value, _ in rolls if value == highest_value]
        is_tie_for_highest = len(top_rollers) > 1

        result_lines = []
        est = pytz.timezone("US/Eastern")

        for name, value, timestamp in rolls:
            if value == highest_value:
                emoji = "⚔️" if is_tie_for_highest else "👑"
            elif value == lowest_value and len(rolls) > 1:
                emoji = "💀"
            else:
                emoji = "🎲"
            result_lines.append(f"{emoji} **{name}** rolled **{value}**")

        # Apply rate limiting before the edit
        await rate_limiter.acquire()
        await interaction.response.edit_message(content="\n".join(result_lines), view=self)

    @discord.ui.button(label="📊", style=discord.ButtonStyle.secondary, custom_id="stats_button", row=0)
    async def stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Import here to avoid circular imports
        from db.operations import get_roll_stats, get_rolls, get_message_info
        from ui.admin_buttons import AdminRollManager
        
        user_id = interaction.user.id
        
        # Rate limit these operations
        await rate_limiter.acquire()
        stats = await get_roll_stats(self.button_id)
        
        await rate_limiter.acquire()
        rolls = await get_rolls(self.button_id)
        
        await rate_limiter.acquire()
        message_info = await get_message_info(self.button_id)

        message = (
            f"📊 **Roll Stats**\n"
            f"- Total rolls: `{stats['total_rolls']}`\n"
            f"- Average roll: `{stats['average_roll']}`\n"
            f"- Latest roll: `{stats['latest_roll_time']}`\n"
        )

        if self.is_authorized(user_id):
            message += "\n🔐 **Admin Info**\n"
            message += f"- Button ID: `{self.button_id}`\n"
            
            if message_info:
                message += f"- Channel ID: `{message_info['channel_id']}`\n"
                message += f"- Message ID: `{message_info['message_id']}`\n"

            if rolls:
                message += "- Recent Rolls:\n"
                est = pytz.timezone("US/Eastern")
                for r in rolls[-5:]:
                    time_str = r["timestamp"].astimezone(est).strftime("%I:%M%p %m/%d/%y") if r["timestamp"] else "Unknown time"
                    message += f"  • {r['user_display_name']} rolled {r['roll']} - `{time_str}`\n"

            admin_view = AdminRollManager(self.button_id, rolls)
            
            # Rate limit the response
            await rate_limiter.acquire()
            await interaction.response.send_message(message, ephemeral=True, view=admin_view)
        else:
            await interaction.response.send_message(message, ephemeral=True)