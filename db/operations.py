import pytz
import logging
from db.connection import get_db_pool

logger = logging.getLogger('discord_bot')

async def save_button_message(button_id, channel_id, message_id):
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO button_messages (button_id, channel_id, message_id) VALUES ($1, $2, $3)",
            str(button_id), channel_id, message_id
        )

async def get_button_messages():
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        return await conn.fetch("SELECT button_id, channel_id, message_id FROM button_messages")

async def get_message_info(button_id):
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT channel_id, message_id FROM button_messages WHERE button_id = $1",
            str(button_id)
        )

async def save_roll(button_id, user_id, user_display_name, roll):
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO rolls (button_id, user_id, user_display_name, roll) VALUES ($1, $2, $3, $4)",
            str(button_id), user_id, user_display_name, roll
        )

async def has_user_rolled(button_id, user_id):
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT 1 FROM rolls WHERE button_id = $1 AND user_id = $2",
            str(button_id), user_id
        )

async def get_rolls(button_id):
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        return await conn.fetch(
            "SELECT user_id, user_display_name, roll, timestamp FROM rolls WHERE button_id = $1",
            str(button_id)
        )

async def get_roll_stats(button_id):
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        total_rolls = await conn.fetchval(
            "SELECT COUNT(*) FROM rolls WHERE button_id = $1",
            str(button_id)
        )
        
        # Get average roll and round to whole number
        if total_rolls > 0:
            avg_roll = await conn.fetchval(
                "SELECT AVG(roll) FROM rolls WHERE button_id = $1",
                str(button_id)
            )
            average_roll = round(avg_roll)  # Round to nearest integer
        else:
            average_roll = 0
            
        latest_timestamp = await conn.fetchval(
            "SELECT timestamp FROM rolls WHERE button_id = $1 ORDER BY timestamp DESC LIMIT 1",
            str(button_id)
        )
        if latest_timestamp:
            est = pytz.timezone("US/Eastern")
            latest_roll_time = latest_timestamp.astimezone(est).strftime("%I:%M%p %m/%d/%y")
        else:
            latest_roll_time = "No rolls yet"

        return {
            "total_rolls": total_rolls,
            "average_roll": average_roll,
            "latest_roll_time": latest_roll_time
        }

async def delete_roll(button_id, user_id):
    db_pool = await get_db_pool()
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM rolls WHERE button_id = $1 AND user_id = $2",
            str(button_id), user_id
        )
        return True