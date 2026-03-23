import asyncio
import logging
import os
from config import BOT_TOKEN, DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)

import ad_bot_legacy

if __name__ == "__main__":
    asyncio.run(ad_bot_legacy.main())
