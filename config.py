import os

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admins who can manage rolls
AUTHORIZED_ADMIN_IDS = [
    int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None,
    int(os.getenv("ADMIN_ID_2")) if os.getenv("ADMIN_ID_2") else None,
    int(os.getenv("ADMIN_ID_3")) if os.getenv("ADMIN_ID_3") else None,
    int(os.getenv("ADMIN_ID_4")) if os.getenv("ADMIN_ID_4") else None,
    int(os.getenv("ADMIN_ID_5")) if os.getenv("ADMIN_ID_5") else None
]

# Filter out None values (in case some environment variables are not set)
AUTHORIZED_ADMIN_IDS = [admin_id for admin_id in AUTHORIZED_ADMIN_IDS if admin_id is not None]

# Rate limiting constants
RATE_LIMIT_RESET_TIME = 1  # seconds - Discord rate limits are typically per-second
MAX_OPERATIONS_PER_SECOND = 45  # Discord allows 50/s but we'll keep a small buffer