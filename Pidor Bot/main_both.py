import asyncio

from classic.handlers import router as classic_game_router
from config import PIDOR_BOT_EXTENDED_TOKEN, PIDOR_BOT_TOKEN
from extended.handlers import router as extended_game_router
from shared.runner import run_both_bots


if __name__ == "__main__":
    asyncio.run(
        run_both_bots(
            PIDOR_BOT_TOKEN,
            PIDOR_BOT_EXTENDED_TOKEN,
            classic_game_router,
            extended_game_router,
        )
    )
