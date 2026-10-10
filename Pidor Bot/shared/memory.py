import logging

from shared.database import load_all_participants, load_chat_state

logger = logging.getLogger(__name__)

players: dict[int, dict[int, dict]] = {}
last_choose_at: dict[str, dict[int, int]] = {}
last_chosen_pidor: dict[str, dict[int, str]] = {}
last_nudge_at: dict[str, dict[int, int]] = {}


async def load_memory_from_db() -> None:
    loaded_players = await load_all_participants()
    loaded_times, loaded_names, loaded_nudges = await load_chat_state()
    players.clear()
    players.update(loaded_players)
    last_choose_at.clear()
    last_choose_at.update(loaded_times)
    last_chosen_pidor.clear()
    last_chosen_pidor.update(loaded_names)
    last_nudge_at.clear()
    last_nudge_at.update(loaded_nudges)
    logger.info(
        "Loaded from SQLite: chats=%s players=%s",
        len(players),
        sum(len(chat) for chat in players.values()),
    )


def is_name_taken(chat_id: int, name: str, exclude_user_id: int) -> bool:
    chat_players = players.get(chat_id, {})
    needle = name.casefold()
    for user_id, row in chat_players.items():
        if user_id == exclude_user_id:
            continue
        if str(row["name"]).casefold() == needle:
            return True
    return False


def find_user_id_by_name(chat_id: int, name: str) -> int:
    chat_players = players.get(chat_id, {})
    needle = name.casefold()
    for user_id, row in chat_players.items():
        if str(row["name"]).casefold() == needle:
            return user_id
    return 0


def find_user_id_by_query(chat_id: int, query: str) -> int:
    cleaned = query.strip().lstrip("@")
    if not cleaned:
        return 0
    if cleaned.isdigit():
        user_id = int(cleaned)
        if user_id in players.get(chat_id, {}):
            return user_id
    by_name = find_user_id_by_name(chat_id, cleaned)
    if by_name != 0:
        return by_name
    needle = cleaned.casefold()
    for user_id, row in players.get(chat_id, {}).items():
        if str(row.get("tg_username", "")).casefold() == needle:
            return user_id
    return 0
