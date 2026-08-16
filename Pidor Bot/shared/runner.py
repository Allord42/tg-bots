import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import DB_DIR, LOG_PATH, command_menu
from shared.database import close_db, init_db
from shared.handlers import router as shared_router
from shared.memory import load_memory_from_db
from shared.middleware import ReloadMemoryMiddleware


def setup_logging() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.INFO)


async def run_bot(
    token: str,
    bot_kind: str,
    game_router: Router,
) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    if not token:
        logger.error("Bot token is missing in .env for %s", bot_kind)
        raise SystemExit(1)

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage(), bot_kind=bot_kind)
    dp.message.middleware(ReloadMemoryMiddleware())
    dp.include_router(shared_router)
    dp.include_router(game_router)

    await init_db()
    await load_memory_from_db()
    await bot.set_my_commands(
        [
            BotCommand(command=name, description=text)
            for name, text in command_menu(bot_kind)
        ]
    )
    logger.info("Bot %s started, logs -> %s", bot_kind, LOG_PATH)
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()
        await bot.session.close()
        logger.info("Bot %s stopped", bot_kind)
