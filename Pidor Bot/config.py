import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "db"
LOG_PATH = DB_DIR / "bot.log"
DB_PATH = DB_DIR / "pidor.db"
JSON_PATH = DB_DIR / "pidor.json"
DUMP_LOG_PATH = DB_DIR / "dump.log"
DUMP_MIN_INTERVAL_SECONDS = 24 * 60 * 60
HEROKU_APP_NAME = "telegram-pidor-bot-classic"

load_dotenv(BASE_DIR / ".env")

PIDOR_BOT_TOKEN = os.getenv("PIDOR_BOT_TOKEN", "")
PIDOR_BOT_EXTENDED_TOKEN = os.getenv("PIDOR_BOT_EXTENDED_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

BOT_KIND_CLASSIC = "classic"
BOT_KIND_EXTENDED = "extended"

SCORE_FIELD = {
    BOT_KIND_CLASSIC: "pidor_score",
    BOT_KIND_EXTENDED: "extended_score",
}
CHOOSE_STARTS_FIELD = {
    BOT_KIND_CLASSIC: "choose_starts_classic",
    BOT_KIND_EXTENDED: "choose_starts_extended",
}

ADMIN_IDS = [
    953469867,
]

COOLDOWN_SECONDS = 10 * 60 * 60  # 10 hours
SLEEP_TIME = 2  # seconds between choose phrases

CMD_SUFFIX = {
    BOT_KIND_CLASSIC: "cl",
    BOT_KIND_EXTENDED: "ex",
}


def choose_pidor_command(
    bot_kind: str,
) -> str:
    return f"choose_pidor_{CMD_SUFFIX[bot_kind]}"


def leaderboard_command(
    bot_kind: str,
) -> str:
    return f"leaderboard_{CMD_SUFFIX[bot_kind]}"


def commands_list(
    bot_kind: str,
) -> str:
    choose = choose_pidor_command(bot_kind)
    board = leaderboard_command(bot_kind)
    return (
        "Вступить - /join\n"
        "Сменить имя (доступно только админам) - /rename\n"
        f"Таблица пидоров - /{board}\n"
        f"Выбрать пидора - /{choose}\n"
        "Узнать информацию - /username_account Имя\n"
        "Указать день рождения - /set_birthday\n"
    )


def command_menu(
    bot_kind: str,
) -> list[tuple[str, str]]:
    return [
        ("join", "Вступить"),
        ("rename", "Сменить имя (админ)"),
        (leaderboard_command(bot_kind), "Таблица пидоров"),
        (choose_pidor_command(bot_kind), "Выбрать пидора"),
        ("username_account", "Карточка участника"),
        ("set_birthday", "День рождения"),
        ("commands", "Список команд"),
    ]


START_MESSAGE = "Пидорасня тебя ждет. Скорее вступай в наше лудоприключение :)\n"
COMMANDS_HELP = "Список доступных команд: /commands"
START_MESSAGE_CLASSIC = START_MESSAGE + "Это классический бот.\n"
START_MESSAGE_EXTENDED = (
    START_MESSAGE + "Это расширенный бот. Счёт и choose отдельные.\n"
)
CHOOSE_PIDOR_MESSAGE = [
    "Настраиваю свои алгоритмы...",
    "Считаю число пи...",
    "Перечитываю труды Эйлера...",
    "Уже почти...",
    "Ещё секунду...",
    "99.99%...",
]
CHOOSE_PIDOR_RESULT = "Очевидно, пидор дня - {name}"

JOIN_MESSAGE = "вступил, красавчик!"

NO_NAME_ERROR = "Имя пустое. Напиши, как к тебе обращаться"
NO_NAME_COMMAND_ERROR = "Сейчас жду имя, а не команду. Напиши текст, например: Вася"
NAME_TOO_LONG_ERROR = "Слишком длинное имя. Максимум 32 символа"
NAME_TAKEN_ERROR = (
    "Ай-ай-ай, какой хитренький жулик!\nТакое имя уже занято. Выбери другое"
)
ALREADY_JOINED_ERROR = "Ты уже в списке участников"
NOT_JOINED_ERROR = "Сначала вступи через /join"
NOBODY_JOINED_ERROR = "Никто не участвует. Сначала /join"
NOT_ADMIN_ERROR = "Только админ может менять имена"
PLAYER_NOT_FOUND_ERROR = "Такого участника нет в этом чате"
BIRTHDAY_FORMAT_ERROR = "Неверный формат. Напиши как 15.03.1999"
WAITING_BIRTHDAY_MESSAGE = "Введите ваш день рождения в формате DD.MM.YYYY"
BIRTHDAY_SAVED_MESSAGE = "День рождения сохранён: {date}"

LEADERBOARD_EMPTY_MESSAGE = "Таблица пуста. Сначала /join"
WAITING_JOIN_NAME_MESSAGE = "Как боту к вам обращаться?"
WAITING_RENAME_TARGET_MESSAGE = "Кого переименовать? Напиши текущее имя участника"
WAITING_RENAME_NAME_MESSAGE = "Какое будет новое имя?"
