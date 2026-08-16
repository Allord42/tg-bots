import asyncio

from config import BOT_KIND_EXTENDED, PIDOR_BOT_EXTENDED_TOKEN
from extended.handlers import router as extended_game_router
from shared.runner import run_bot


if __name__ == "__main__":
    asyncio.run(
        run_bot(PIDOR_BOT_EXTENDED_TOKEN, BOT_KIND_EXTENDED, extended_game_router)
    )
