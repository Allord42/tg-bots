import logging
from datetime import datetime

from aiogram.types import Message

from config import (
    ADMIN_IDS,
    BIRTHDAY_FORMAT_ERROR,
    NAME_TOO_LONG_ERROR,
    NO_NAME_COMMAND_ERROR,
    NO_NAME_ERROR,
)

logger = logging.getLogger(__name__)


def log_event(message: Message, action: str, detail: str = "") -> None:
    user = message.from_user
    user_id = user.id if user else 0
    username = user.username if user and user.username else "-"
    full_name = user.full_name if user else "-"
    text = detail if detail else (message.text or "")
    logger.info(
        "%s | chat_id=%s user_id=%s @%s (%s) | %s",
        action,
        message.chat.id,
        user_id,
        username,
        full_name,
        text,
    )


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def format_remaining(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0 and minutes > 0:
        return f"{hours} ч. {minutes} мин."
    if hours > 0:
        return f"{hours} ч."
    if minutes > 0:
        return f"{minutes} мин."
    return "Меньше минуты"


def validate_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        return NO_NAME_ERROR
    if cleaned.startswith("/"):
        return NO_NAME_COMMAND_ERROR
    if len(cleaned) > 32:
        return NAME_TOO_LONG_ERROR
    return ""


def parse_birthday(raw: str) -> tuple[int, str]:
    cleaned = raw.strip()
    try:
        parsed = datetime.strptime(cleaned, "%d.%m.%Y")
    except ValueError:
        return 0, BIRTHDAY_FORMAT_ERROR
    packed = parsed.year * 10000 + parsed.month * 100 + parsed.day
    return packed, ""


def format_birthday(packed: int) -> str:
    if packed == 0:
        return ""
    year = packed // 10000
    month = (packed % 10000) // 100
    day = packed % 100
    return f"{day:02d}.{month:02d}.{year}"


def format_joined_at(unix_time: int) -> str:
    if unix_time == 0:
        return ""
    return datetime.fromtimestamp(unix_time).strftime("%d.%m.%Y %H:%M")


def extract_command_arg(text: str) -> str:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


def user_account(
    user_id: int,
    player: dict,
    tg_username: str,
    full_name: str,
    is_premium: bool,
) -> str:
    username_shown = tg_username if tg_username else "-"
    full_name_shown = full_name if full_name else "-"
    lines = [
        f"user_id: {user_id}",
        f"username: {username_shown}",
        f"full_name: {full_name_shown}",
    ]

    joined_at = int(player.get("time_joined", 0)) if player else 0
    joined_text = format_joined_at(joined_at)
    if joined_text:
        lines.append(f"вступил: {joined_text}")
    else:
        lines.append("вступил: —")

    birthday_text = (
        format_birthday(int(player.get("birthday_date", 0))) if player else ""
    )
    if birthday_text:
        lines.append(f"день рождения: {birthday_text}")
    else:
        lines.append("день рождения: не указан. /set_birthday")

    lines.append(f"admin: {'да' if is_admin(user_id) else 'нет'}")
    lines.append(f"premium: {'да' if is_premium else 'нет'}")

    if player:
        lines.extend(
            [
                f"игровое имя: {player['name']}",
                f"пидоров classic: {player.get('pidor_score', 0)}",
                f"пидоров extended: {player.get('extended_score', 0)}",
                f"запусков classic: {player.get('choose_starts_classic', 0)}",
                f"запусков extended: {player.get('choose_starts_extended', 0)}",
            ]
        )
    else:
        lines.append("в игре: нет, сначала /join")

    return "\n".join(lines)
