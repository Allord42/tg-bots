import asyncio

from classic.handlers import router as classic_game_router
from config import BOT_KIND_CLASSIC, PIDOR_BOT_TOKEN
from shared.runner import run_bot


if __name__ == "__main__":
    asyncio.run(run_bot(PIDOR_BOT_TOKEN, BOT_KIND_CLASSIC, classic_game_router))
