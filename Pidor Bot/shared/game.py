import asyncio
import random
import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import (
    BOT_KIND_CLASSIC,
    CHOOSE_PIDOR_MESSAGE,
    CHOOSE_PIDOR_RESULT,
    CHOOSE_STARTS_FIELD,
    COOLDOWN_SECONDS,
    LEADERBOARD_EMPTY_MESSAGE,
    NOBODY_JOINED_ERROR,
    SCORE_FIELD,
    SLEEP_TIME,
    choose_pidor_command,
    leaderboard_command,
)
from shared.database import record_successful_choose
from shared.memory import last_choose_at, last_chosen_pidor, players
from shared.text_utils import (
    choose_result_mention,
    fetch_tg_user,
    format_remaining,
    log_event,
)


def make_game_router(bot_kind: str) -> Router:
    router = Router()
    score_field = SCORE_FIELD[bot_kind]
    starts_field = CHOOSE_STARTS_FIELD[bot_kind]
    choose_cmd = choose_pidor_command(bot_kind)
    board_cmd = leaderboard_command(bot_kind)
    board_title = (
        "Таблица пидоров (classic):"
        if bot_kind == BOT_KIND_CLASSIC
        else "Таблица пидоров (extended):"
    )

    @router.message(Command(board_cmd))
    async def cmd_leaderboard(message: Message) -> None:
        chat_id = message.chat.id
        chat_players = players.get(chat_id, {})
        log_event(message, f"CMD /{board_cmd}")

        if not chat_players:
            await message.answer(LEADERBOARD_EMPTY_MESSAGE)
            return

        ranked = sorted(
            chat_players.values(),
            key=lambda row: int(row.get(score_field, 0)),
            reverse=True,
        )

        lines = [board_title]
        index = 1
        for row in ranked:
            lines.append(f"{index}. {row['name']} — {row.get(score_field, 0)}")
            index += 1

        await message.answer("\n".join(lines))

    @router.message(Command(choose_cmd))
    async def cmd_choose_pidor(message: Message) -> None:
        chat_id = message.chat.id
        chat_players = players.get(chat_id, {})
        log_event(message, f"CMD /{choose_cmd}")

        if not chat_players:
            await message.answer(NOBODY_JOINED_ERROR)
            return

        now = int(time.time())
        previous = last_choose_at.get(bot_kind, {}).get(chat_id, 0)
        if previous > 0:
            elapsed = now - previous
            if elapsed < COOLDOWN_SECONDS:
                remaining = COOLDOWN_SECONDS - elapsed
                log_event(message, "CHOOSE cooldown", format_remaining(remaining))
                await message.answer(
                    f"Выбор пидора через {format_remaining(remaining)}"
                )
                return

        if message.from_user is None:
            return

        starter_id = message.from_user.id
        chosen_id = random.choice(list(chat_players.keys()))
        chosen = chat_players[chosen_id]
        chosen[score_field] = int(chosen.get(score_field, 0)) + 1
        if starter_id in chat_players:
            chat_players[starter_id][starts_field] = (
                int(chat_players[starter_id].get(starts_field, 0)) + 1
            )
        if bot_kind not in last_choose_at:
            last_choose_at[bot_kind] = {}
            last_chosen_pidor[bot_kind] = {}
        last_choose_at[bot_kind][chat_id] = now
        last_chosen_pidor[bot_kind][chat_id] = str(chosen["name"])
        await record_successful_choose(
            chat_id=chat_id,
            starter_user_id=starter_id,
            chosen_user_id=chosen_id,
            chosen_name=str(chosen["name"]),
            last_choose_at=now,
            bot_kind=bot_kind,
        )
        log_event(
            message,
            "CHOOSE ok",
            f"bot={bot_kind} chosen_user_id={chosen_id} name={chosen['name']} "
            f"score={chosen[score_field]}",
        )

        for text in CHOOSE_PIDOR_MESSAGE:
            await message.answer(text)
            await asyncio.sleep(SLEEP_TIME)

        tg_user = await fetch_tg_user(message, chosen_id)
        tg_username = tg_user.username if tg_user.username else str(
            chosen.get("tg_username", "")
        )
        mention = choose_result_mention(
            chosen_id,
            str(chosen["name"]),
            tg_username,
        )
        await message.answer(
            CHOOSE_PIDOR_RESULT.format(name=mention),
            parse_mode="HTML",
        )

    return router
