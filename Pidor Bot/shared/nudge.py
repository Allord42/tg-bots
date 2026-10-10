import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import (
    NUDGE_AFTER_SECONDS,
    NUDGE_CHECK_SECONDS,
    NUDGE_MESSAGE,
    choose_pidor_command,
)
from shared.database import update_last_nudge
from shared.memory import last_choose_at, last_nudge_at, load_memory_from_db, players

logger = logging.getLogger(__name__)


def _should_nudge(
    last_choose: int,
    last_nudge: int,
    now: int,
) -> bool:
    if last_choose <= 0:
        return False
    if now - last_choose < NUDGE_AFTER_SECONDS:
        return False
    if last_nudge < last_choose:
        return True
    return now - last_nudge >= NUDGE_AFTER_SECONDS


async def send_due_nudges(
    bots: dict[str, Bot],
) -> None:
    await load_memory_from_db()
    now = int(time.time())
    for bot_kind, bot in bots.items():
        choose_times = last_choose_at.get(bot_kind, {})
        nudge_times = last_nudge_at.get(bot_kind, {})
        command = choose_pidor_command(bot_kind)
        text = f"{NUDGE_MESSAGE}\n/{command}"
        for chat_id, last_choose in choose_times.items():
            if not players.get(chat_id, {}):
                continue
            last_nudge = nudge_times.get(chat_id, 0)
            if not _should_nudge(last_choose, last_nudge, now):
                continue
            try:
                await bot.send_message(chat_id, text)
                logger.info(
                    "Nudge sent bot=%s chat_id=%s command=/%s",
                    bot_kind,
                    chat_id,
                    command,
                )
            except TelegramForbiddenError:
                logger.warning(
                    "Nudge forbidden bot=%s chat_id=%s",
                    bot_kind,
                    chat_id,
                )
            except TelegramBadRequest:
                logger.warning(
                    "Nudge bad request bot=%s chat_id=%s",
                    bot_kind,
                    chat_id,
                )
            if bot_kind not in last_nudge_at:
                last_nudge_at[bot_kind] = {}
            last_nudge_at[bot_kind][chat_id] = now
            await update_last_nudge(chat_id, bot_kind, now)


async def run_nudge_loop(
    bots: dict[str, Bot],
    stop_event: asyncio.Event,
) -> None:
    await send_due_nudges(bots)
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=NUDGE_CHECK_SECONDS)
        except asyncio.TimeoutError:
            try:
                await send_due_nudges(bots)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Nudge check failed")
