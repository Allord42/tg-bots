import logging

import aiosqlite

from config import (
    BOT_KIND_CLASSIC,
    BOT_KIND_EXTENDED,
    CHOOSE_STARTS_FIELD,
    DB_DIR,
    DB_PATH,
    SCORE_FIELD,
)

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 5

MIGRATIONS: dict[int, str] = {
    1: """
        CREATE TABLE IF NOT EXISTS participants (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            display_name TEXT NOT NULL,
            tg_username TEXT NOT NULL DEFAULT '',
            time_joined INTEGER NOT NULL,
            pidor_score INTEGER NOT NULL DEFAULT 0,
            choose_starts INTEGER NOT NULL DEFAULT 0,
            is_admin INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        );
        """,
    2: """
        CREATE TABLE IF NOT EXISTS chat_state (
            chat_id INTEGER PRIMARY KEY,
            last_choose_at INTEGER NOT NULL DEFAULT 0
        );
        """,
    3: """
        ALTER TABLE chat_state ADD COLUMN chosen_pidor TEXT NOT NULL DEFAULT '';
        UPDATE chat_state SET chosen_pidor = 'Саня' WHERE chosen_pidor = '';
        """,
    4: """
        CREATE TABLE participants_new (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            display_name TEXT NOT NULL,
            tg_username TEXT NOT NULL DEFAULT '',
            birthday_date INTEGER NOT NULL DEFAULT 0,
            time_joined INTEGER NOT NULL,
            pidor_score INTEGER NOT NULL DEFAULT 0,
            choose_starts INTEGER NOT NULL DEFAULT 0,
            is_admin INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        );
        INSERT INTO participants_new (
            chat_id, user_id, display_name, tg_username, birthday_date,
            time_joined, pidor_score, choose_starts, is_admin
        )
        SELECT
            chat_id, user_id, display_name, tg_username, 0,
            time_joined, pidor_score, choose_starts, is_admin
        FROM participants;
        DROP TABLE participants;
        ALTER TABLE participants_new RENAME TO participants;
        """,
    5: """
        CREATE TABLE participants_new (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            display_name TEXT NOT NULL,
            tg_username TEXT NOT NULL DEFAULT '',
            birthday_date INTEGER NOT NULL DEFAULT 0,
            time_joined INTEGER NOT NULL,
            pidor_score INTEGER NOT NULL DEFAULT 0,
            extended_score INTEGER NOT NULL DEFAULT 0,
            choose_starts_classic INTEGER NOT NULL DEFAULT 0,
            choose_starts_extended INTEGER NOT NULL DEFAULT 0,
            is_admin INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        );
        INSERT INTO participants_new (
            chat_id, user_id, display_name, tg_username, birthday_date,
            time_joined, pidor_score, extended_score,
            choose_starts_classic, choose_starts_extended, is_admin
        )
        SELECT
            chat_id, user_id, display_name, tg_username, birthday_date,
            time_joined, pidor_score, 0,
            choose_starts, 0, is_admin
        FROM participants;
        DROP TABLE participants;
        ALTER TABLE participants_new RENAME TO participants;

        CREATE TABLE chat_state_new (
            chat_id INTEGER NOT NULL,
            bot_kind TEXT NOT NULL,
            last_choose_at INTEGER NOT NULL DEFAULT 0,
            chosen_pidor TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (chat_id, bot_kind)
        );
        INSERT INTO chat_state_new (chat_id, bot_kind, last_choose_at, chosen_pidor)
        SELECT chat_id, 'classic', last_choose_at, chosen_pidor FROM chat_state;
        DROP TABLE chat_state;
        ALTER TABLE chat_state_new RENAME TO chat_state;
        """,
}

_connection: aiosqlite.Connection


async def init_db() -> None:
    global _connection
    DB_DIR.mkdir(parents=True, exist_ok=True)
    _connection = await aiosqlite.connect(DB_PATH)
    _connection.row_factory = aiosqlite.Row
    await _connection.execute("PRAGMA foreign_keys = ON")
    await _connection.execute("PRAGMA journal_mode=WAL")
    await _connection.execute("PRAGMA busy_timeout=5000")
    await _ensure_schema()
    logger.info("SQLite ready -> %s (schema v%s)", DB_PATH, SCHEMA_VERSION)


async def close_db() -> None:
    await _connection.close()
    logger.info("SQLite closed")


def get_connection() -> aiosqlite.Connection:
    return _connection


async def _ensure_schema() -> None:
    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL
        )
        """
    )
    await _connection.commit()

    cursor = await _connection.execute(
        "SELECT version FROM schema_meta WHERE id = 1"
    )
    row = await cursor.fetchone()
    current = int(row["version"]) if row is not None else 0

    for version in sorted(MIGRATIONS.keys()):
        if version <= current:
            continue
        await _connection.executescript(MIGRATIONS[version])
        await _connection.execute(
            """
            INSERT INTO schema_meta (id, version) VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET version = excluded.version
            """,
            (version,),
        )
        await _connection.commit()
        logger.info("Applied DB migration v%s", version)


async def add_participant(
    chat_id: int,
    user_id: int,
    display_name: str,
    tg_username: str,
    time_joined: int,
    is_admin: int,
) -> None:
    await _connection.execute(
        """
        INSERT INTO participants (
            chat_id, user_id, display_name, tg_username, birthday_date,
            time_joined, pidor_score, extended_score,
            choose_starts_classic, choose_starts_extended, is_admin
        )
        VALUES (?, ?, ?, ?, 0, ?, 0, 0, 0, 0, ?)
        """,
        (chat_id, user_id, display_name, tg_username, time_joined, is_admin),
    )
    await _connection.commit()


async def update_display_name(
    chat_id: int,
    user_id: int,
    display_name: str,
) -> None:
    await _connection.execute(
        """
        UPDATE participants
        SET display_name = ?
        WHERE chat_id = ? AND user_id = ?
        """,
        (display_name, chat_id, user_id),
    )
    await _connection.commit()


async def update_birthday_date(
    chat_id: int,
    user_id: int,
    birthday_date: int,
) -> None:
    await _connection.execute(
        """
        UPDATE participants
        SET birthday_date = ?
        WHERE chat_id = ? AND user_id = ?
        """,
        (birthday_date, chat_id, user_id),
    )
    await _connection.commit()


async def record_successful_choose(
    chat_id: int,
    starter_user_id: int,
    chosen_user_id: int,
    chosen_name: str,
    last_choose_at: int,
    bot_kind: str,
) -> None:
    if bot_kind not in SCORE_FIELD:
        raise ValueError(bot_kind)
    score_col = SCORE_FIELD[bot_kind]
    starts_col = CHOOSE_STARTS_FIELD[bot_kind]
    await _connection.execute(
        f"""
        UPDATE participants
        SET {score_col} = {score_col} + 1
        WHERE chat_id = ? AND user_id = ?
        """,
        (chat_id, chosen_user_id),
    )
    await _connection.execute(
        f"""
        UPDATE participants
        SET {starts_col} = {starts_col} + 1
        WHERE chat_id = ? AND user_id = ?
        """,
        (chat_id, starter_user_id),
    )
    await _connection.execute(
        """
        INSERT INTO chat_state (chat_id, bot_kind, last_choose_at, chosen_pidor)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id, bot_kind) DO UPDATE SET
            last_choose_at = excluded.last_choose_at,
            chosen_pidor = excluded.chosen_pidor
        """,
        (chat_id, bot_kind, last_choose_at, chosen_name),
    )
    await _connection.commit()


async def load_all_participants() -> dict[int, dict[int, dict]]:
    cursor = await _connection.execute("SELECT * FROM participants")
    rows = await cursor.fetchall()
    loaded: dict[int, dict[int, dict]] = {}
    for row in rows:
        chat_id = int(row["chat_id"])
        user_id = int(row["user_id"])
        if chat_id not in loaded:
            loaded[chat_id] = {}
        loaded[chat_id][user_id] = {
            "name": str(row["display_name"]),
            "pidor_score": int(row["pidor_score"]),
            "extended_score": int(row["extended_score"]),
            "tg_username": str(row["tg_username"]),
            "birthday_date": int(row["birthday_date"]),
            "time_joined": int(row["time_joined"]),
            "choose_starts_classic": int(row["choose_starts_classic"]),
            "choose_starts_extended": int(row["choose_starts_extended"]),
            "is_admin": int(row["is_admin"]),
        }
    return loaded


async def load_chat_state() -> tuple[dict[str, dict[int, int]], dict[str, dict[int, str]]]:
    cursor = await _connection.execute(
        "SELECT chat_id, bot_kind, last_choose_at, chosen_pidor FROM chat_state"
    )
    rows = await cursor.fetchall()
    choose_times: dict[str, dict[int, int]] = {
        BOT_KIND_CLASSIC: {},
        BOT_KIND_EXTENDED: {},
    }
    chosen_names: dict[str, dict[int, str]] = {
        BOT_KIND_CLASSIC: {},
        BOT_KIND_EXTENDED: {},
    }
    for row in rows:
        kind = str(row["bot_kind"])
        chat_id = int(row["chat_id"])
        if kind not in choose_times:
            choose_times[kind] = {}
            chosen_names[kind] = {}
        choose_times[kind][chat_id] = int(row["last_choose_at"])
        chosen_names[kind][chat_id] = str(row["chosen_pidor"])
    return choose_times, chosen_names
