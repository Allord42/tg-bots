import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User

from config import (
    ALREADY_JOINED_ERROR,
    BIRTHDAY_SAVED_MESSAGE,
    BOT_KIND_EXTENDED,
    COMMANDS_HELP,
    JOIN_MESSAGE,
    NAME_TAKEN_ERROR,
    NOBODY_JOINED_ERROR,
    NOT_ADMIN_ERROR,
    NOT_JOINED_ERROR,
    PLAYER_NOT_FOUND_ERROR,
    START_MESSAGE_CLASSIC,
    START_MESSAGE_EXTENDED,
    WAITING_BIRTHDAY_MESSAGE,
    WAITING_JOIN_NAME_MESSAGE,
    WAITING_RENAME_NAME_MESSAGE,
    WAITING_RENAME_TARGET_MESSAGE,
    commands_list,
)
from shared.database import add_participant, update_birthday_date, update_display_name
from shared.memory import (
    find_user_id_by_name,
    find_user_id_by_query,
    is_name_taken,
    players,
)
from shared.states import BirthdayForm, NameForm
from shared.text_utils import (
    extract_command_arg,
    format_birthday,
    is_admin,
    log_event,
    parse_birthday,
    user_account,
    validate_name,
)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, bot_kind: str) -> None:
    log_event(message, "CMD /start")
    intro = (
        START_MESSAGE_EXTENDED
        if bot_kind == BOT_KIND_EXTENDED
        else START_MESSAGE_CLASSIC
    )
    await message.answer(intro + COMMANDS_HELP)


@router.message(Command("commands"))
async def cmd_commands(message: Message, bot_kind: str) -> None:
    log_event(message, "CMD /commands")
    await message.answer(commands_list(bot_kind))


async def fetch_tg_user(message: Message, user_id: int) -> User:
    try:
        member = await message.bot.get_chat_member(message.chat.id, user_id)
        return member.user
    except TelegramBadRequest:
        if message.from_user and message.from_user.id == user_id:
            return message.from_user
        return User(id=user_id, is_bot=False, first_name="-")


@router.message(Command("username_account"))
async def cmd_username_account(message: Message) -> None:
    if message.from_user is None:
        return

    chat_id = message.chat.id
    query = extract_command_arg(message.text if message.text else "")
    log_event(message, "CMD /username_account", query if query else "self")

    if query:
        target_id = find_user_id_by_query(chat_id, query)
        if target_id == 0:
            await message.answer(PLAYER_NOT_FOUND_ERROR)
            return
        player = players[chat_id][target_id]
        tg_user = await fetch_tg_user(message, target_id)
        text = user_account(
            user_id=target_id,
            player=player,
            tg_username=tg_user.username if tg_user.username else str(player.get("tg_username", "")),
            full_name=tg_user.full_name,
            is_premium=bool(tg_user.is_premium),
        )
        await message.answer(text)
        return

    user_id = message.from_user.id
    player = players.get(chat_id, {}).get(user_id, {})
    tg_username = message.from_user.username if message.from_user.username else ""
    text = user_account(
        user_id=user_id,
        player=player,
        tg_username=tg_username,
        full_name=message.from_user.full_name,
        is_premium=bool(message.from_user.is_premium),
    )
    await message.answer(text)


@router.message(Command("set_birthday"))
async def cmd_set_birthday(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    log_event(message, "CMD /set_birthday")

    if user_id not in players.get(chat_id, {}):
        await message.answer(NOT_JOINED_ERROR)
        return

    await state.set_state(BirthdayForm.waiting_date)
    await message.answer(WAITING_BIRTHDAY_MESSAGE)


@router.message(BirthdayForm.waiting_date, F.text)
async def cmd_set_birthday_date(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    if user_id not in players.get(chat_id, {}):
        await state.clear()
        await message.answer(NOT_JOINED_ERROR)
        return

    raw_text = message.text if message.text else ""
    packed, error = parse_birthday(raw_text)
    if error:
        log_event(message, "BIRTHDAY invalid", raw_text)
        await message.answer(error)
        return

    players[chat_id][user_id]["birthday_date"] = packed
    await update_birthday_date(chat_id, user_id, packed)
    await state.clear()
    shown = format_birthday(packed)
    log_event(message, "BIRTHDAY ok", shown)
    await message.answer(BIRTHDAY_SAVED_MESSAGE.format(date=shown))


@router.message(Command("join"))
async def cmd_join(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    log_event(message, "CMD /join")

    if chat_id not in players:
        players[chat_id] = {}

    if user_id in players[chat_id]:
        await message.answer(ALREADY_JOINED_ERROR)
        return

    await state.set_state(NameForm.waiting_join_name)
    await message.answer(WAITING_JOIN_NAME_MESSAGE)


@router.message(NameForm.waiting_join_name, F.text)
async def cmd_join_name(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    raw_text = message.text if message.text else ""
    error = validate_name(raw_text)
    if error:
        log_event(message, "JOIN name invalid", error)
        await message.answer(error)
        return

    name = raw_text.strip()
    chat_id = message.chat.id
    user_id = message.from_user.id

    if is_name_taken(chat_id, name, 0):
        log_event(message, "JOIN name taken", name)
        await message.answer(NAME_TAKEN_ERROR)
        return

    if chat_id not in players:
        players[chat_id] = {}

    tg_username = message.from_user.username if message.from_user.username else ""
    now = int(time.time())
    admin_flag = 1 if is_admin(user_id) else 0
    players[chat_id][user_id] = {
        "name": name,
        "pidor_score": 0,
        "extended_score": 0,
        "tg_username": tg_username,
        "birthday_date": 0,
        "time_joined": now,
        "choose_starts_classic": 0,
        "choose_starts_extended": 0,
        "is_admin": admin_flag,
    }
    await add_participant(
        chat_id=chat_id,
        user_id=user_id,
        display_name=name,
        tg_username=tg_username,
        time_joined=now,
        is_admin=admin_flag,
    )
    await state.clear()
    log_event(message, "JOIN ok", f"name={name}")
    await message.answer(f"{name} {JOIN_MESSAGE}")


@router.message(Command("rename"))
async def cmd_rename(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    user_id = message.from_user.id
    log_event(message, "CMD /rename")

    if not is_admin(user_id):
        log_event(message, "RENAME denied")
        await message.answer(NOT_ADMIN_ERROR)
        return

    chat_players = players.get(message.chat.id, {})
    if not chat_players:
        await message.answer(NOBODY_JOINED_ERROR)
        return

    await state.set_state(NameForm.waiting_rename_target)
    await message.answer(WAITING_RENAME_TARGET_MESSAGE)


@router.message(NameForm.waiting_rename_target, F.text)
async def cmd_rename_target(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer(NOT_ADMIN_ERROR)
        return

    raw_text = message.text if message.text else ""
    target_name = raw_text.strip()
    chat_id = message.chat.id
    target_user_id = find_user_id_by_name(chat_id, target_name)

    if target_user_id == 0:
        log_event(message, "RENAME target not found", target_name)
        await message.answer(PLAYER_NOT_FOUND_ERROR)
        return

    await state.update_data(target_user_id=target_user_id, old_name=target_name)
    await state.set_state(NameForm.waiting_rename_new_name)
    log_event(
        message,
        "RENAME target ok",
        f"target_user_id={target_user_id} old_name={target_name}",
    )
    await message.answer(WAITING_RENAME_NAME_MESSAGE)


@router.message(NameForm.waiting_rename_new_name, F.text)
async def cmd_rename_new_name(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer(NOT_ADMIN_ERROR)
        return

    raw_text = message.text if message.text else ""
    error = validate_name(raw_text)
    if error:
        await message.answer(error)
        return

    new_name = raw_text.strip()
    chat_id = message.chat.id
    data = await state.get_data()
    target_user_id = int(data.get("target_user_id", 0))
    chat_players = players.get(chat_id, {})

    if target_user_id == 0 or target_user_id not in chat_players:
        await state.clear()
        await message.answer(PLAYER_NOT_FOUND_ERROR)
        return

    if is_name_taken(chat_id, new_name, target_user_id):
        await message.answer(NAME_TAKEN_ERROR)
        return

    old_name = str(chat_players[target_user_id]["name"])
    chat_players[target_user_id]["name"] = new_name
    await update_display_name(chat_id, target_user_id, new_name)
    await state.clear()
    log_event(
        message,
        "RENAME ok",
        f"target_user_id={target_user_id} {old_name} -> {new_name}",
    )
    await message.answer(f"{old_name} теперь {new_name}")
