import asyncio
import logging
import os
import signal
import sys
from collections.abc import Callable

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import (
    BOT_KIND_CLASSIC,
    BOT_KIND_EXTENDED,
    DB_DIR,
    LOG_PATH,
    command_menu,
)
from shared.database import close_db, init_db
from shared.handlers import make_shared_router
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


def setup_dispatcher(
    bot_kind: str,
    game_router: Router,
) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage(), bot_kind=bot_kind)
    dp.message.middleware(ReloadMemoryMiddleware())
    dp.include_router(make_shared_router())
    dp.include_router(game_router)
    return dp


async def setup_bot_commands(
    bot: Bot,
    bot_kind: str,
) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command=name, description=text)
            for name, text in command_menu(bot_kind)
        ]
    )


async def _handle_health(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    await reader.read(1024)
    body = b"OK"
    writer.write(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Content-Length: 2\r\n"
        b"Connection: close\r\n"
        b"\r\n" + body
    )
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def serve_health_http(
    port: int,
    servers: list[asyncio.AbstractServer],
    stop_event: asyncio.Event,
) -> None:
    server = await asyncio.start_server(_handle_health, "0.0.0.0", port)
    servers.append(server)
    async with server:
        await stop_event.wait()


def _install_stop_signals(
    stop: Callable[[], None],
) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop)
        except NotImplementedError:
            return


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
    dp = setup_dispatcher(bot_kind, game_router)

    await init_db()
    await load_memory_from_db()
    await setup_bot_commands(bot, bot_kind)
    logger.info("Bot %s started, logs -> %s", bot_kind, LOG_PATH)
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()
        await bot.session.close()
        logger.info("Bot %s stopped", bot_kind)


async def run_both_bots(
    classic_token: str,
    extended_token: str,
    classic_router: Router,
    extended_router: Router,
) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    if not classic_token:
        logger.error("Bot token is missing in .env for classic")
        raise SystemExit(1)
    if not extended_token:
        logger.error("Bot token is missing in .env for extended")
        raise SystemExit(1)

    bot_classic = Bot(token=classic_token)
    bot_extended = Bot(token=extended_token)
    dp_classic = setup_dispatcher(BOT_KIND_CLASSIC, classic_router)
    dp_extended = setup_dispatcher(BOT_KIND_EXTENDED, extended_router)

    await init_db()
    await load_memory_from_db()
    await setup_bot_commands(bot_classic, BOT_KIND_CLASSIC)
    await setup_bot_commands(bot_extended, BOT_KIND_EXTENDED)

    health_servers: list[asyncio.AbstractServer] = []
    stop_event = asyncio.Event()
    port_text = os.getenv("PORT", "")

    def request_stop() -> None:
        stop_event.set()
        dp_classic.stop_polling()
        dp_extended.stop_polling()
        for server in health_servers:
            server.close()

    _install_stop_signals(request_stop)
    logger.info("Both bots started, logs -> %s", LOG_PATH)

    tasks = [
        asyncio.create_task(
            dp_classic.start_polling(bot_classic, handle_signals=False)
        ),
        asyncio.create_task(
            dp_extended.start_polling(bot_extended, handle_signals=False)
        ),
    ]
    if port_text:
        port = int(port_text)
        tasks.append(
            asyncio.create_task(
                serve_health_http(port, health_servers, stop_event)
            )
        )
        logger.info("Health HTTP on 0.0.0.0:%s", port)

    try:
        await asyncio.gather(*tasks)
    finally:
        request_stop()
        await close_db()
        await bot_classic.session.close()
        await bot_extended.session.close()
        logger.info("Both bots stopped")
