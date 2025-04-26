''' RNGesus Test Bot Application '''

import os
import uuid
import random
import asyncpg
import discord
from discord.ext import commands
from discord import app_commands

# Intents and bot setup.
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

DATABASE_URL = os.getenv("DATABASE_URL")

class RollButton(discord.ui.View):
    def __init__(self, button_id=None):
        super().__init__(timeout=None)
        self.button_id = button_id or uuid.uuid4()
        self.pool = None

    async def ensure_pool(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(DATABASE_URL)

    async def fetch_rolls(self):
        await self.ensure_pool()
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT user_display_name, roll FROM rolls WHERE button_id = $1",
                self.button_id
            )

    async def has_rolled(self, user_id):
        await self.ensure_pool()
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT 1 FROM rolls WHERE button_id = $1 AND user_id = $2",
                self.button_id, user_id
            )

    async def save_roll(self, user_id, user_display_name, roll):
        await self.ensure_pool()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO rolls (button_id, user_id, user_display_name, roll) VALUES ($1, $2, $3, $4)",
                self.button_id, user_id, user_display_name, roll
            )

    @discord.ui.button(label="🎲 CLICK HERE TO ROLL!", style=discord.ButtonStyle.primary, custom_id="roll_button")
    async def roll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        user_display_name = interaction.user.display_name

        if await self.has_rolled(user_id):
            await interaction.response.send_message(
                "‼️ You've already rolled on this item ‼️",
                ephemeral=True
            )
            return

        roll = random.randint(1, 100)
        await self.save_roll(user_id, user_display_name, roll)

        results = await self.fetch_rolls()
        rolls = [(r["user_display_name"], r["roll"]) for r in results]
        highest = max(rolls, key=lambda x: x[1])
        lowest = min(rolls, key=lambda x: x[1])

        result_lines = []
        for name, value in rolls:
            if name == highest[0] and value == highest[1]:
                emoji = "👑"
            elif name == lowest[0] and value == lowest[1] and len(rolls) > 1:
                emoji = "💀"
            else:
                emoji = "🎲"
            result_lines.append(f"{emoji} **{name}** rolled **{value}**")

        await interaction.response.edit_message(content="\n".join(result_lines), view=self)


@bot.tree.command(name="rollbutton", description="Post a roll button")
async def rollbutton(interaction: discord.Interaction):
    view = RollButton()
    await view.ensure_pool()

    # Send the message with view and wait for it to complete.
    await interaction.response.send_message(
        content="🎲 Click the button to roll!",
        view=view,
        ephemeral=False
    )
    message = await interaction.original_response()

    # Save button instance location for restoration
    async with view.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO button_messages (button_id, channel_id, message_id) VALUES ($1, $2, $3)",
            str(view.button_id),
            interaction.channel.id,
            message.id
        )


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print(f"🔁 Synced slash commands")
    except Exception as e:
        print(f"❌ Slash command sync failed: {e}")

    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT button_id, channel_id, message_id FROM button_messages")

        for row in rows:
            button_id = row["button_id"]
            channel = bot.get_channel(row["channel_id"])
            if not channel:
                continue
            try:
                msg = await channel.fetch_message(row["message_id"])
                view = RollButton(button_id=button_id)
                await msg.edit(view=view)
                print(f"🔁 Restored view on message {msg.id} in channel {channel.id}")
            except Exception as e:
                print(f"⚠️ Failed to restore view on message {row['message_id']}: {e}")

    except Exception as e:
        print(f"❌ View restore error: {e}")


bot.run(os.getenv("BOT_TOKEN"))