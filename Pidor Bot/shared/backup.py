import json
import shutil
import sqlite3
import subprocess
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

from config import (
    DATABASE_URL,
    DB_DIR,
    DB_PATH,
    DUMP_LOG_PATH,
    HEROKU_APP_NAME,
    JSON_PATH,
)
from shared.database import POSTGRES_SCHEMA, SCHEMA_VERSION, postgres_dsn

PARTICIPANT_FIELDS = [
    "chat_id",
    "user_id",
    "display_name",
    "tg_username",
    "birthday_date",
    "time_joined",
    "pidor_score",
    "extended_score",
    "choose_starts_classic",
    "choose_starts_extended",
    "is_admin",
]
CHAT_STATE_FIELDS = [
    "chat_id",
    "bot_kind",
    "last_choose_at",
    "chosen_pidor",
    "last_nudge_at",
]


def split_sql_statements(
    script: str,
) -> list[str]:
    statements: list[str] = []
    for raw in script.split(";"):
        statement = raw.strip()
        if statement:
            statements.append(statement)
    return statements


def resolve_database_url() -> str:
    if DATABASE_URL:
        return DATABASE_URL
    heroku = shutil.which("heroku")
    if not heroku:
        return ""
    completed = subprocess.run(
        [heroku, "config:get", "DATABASE_URL", "--app", HEROKU_APP_NAME],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _row_to_participant(
    row: object,
) -> dict:
    mapping = dict(row)
    return {
        "chat_id": int(mapping["chat_id"]),
        "user_id": int(mapping["user_id"]),
        "display_name": str(mapping["display_name"]),
        "tg_username": str(mapping["tg_username"]),
        "birthday_date": int(mapping["birthday_date"]),
        "time_joined": int(mapping["time_joined"]),
        "pidor_score": int(mapping["pidor_score"]),
        "extended_score": int(mapping["extended_score"]),
        "choose_starts_classic": int(mapping["choose_starts_classic"]),
        "choose_starts_extended": int(mapping["choose_starts_extended"]),
        "is_admin": int(mapping["is_admin"]),
    }


def _row_to_chat_state(
    row: object,
) -> dict:
    mapping = dict(row)
    last_nudge = 0
    if "last_nudge_at" in mapping:
        last_nudge = int(mapping["last_nudge_at"])
    return {
        "chat_id": int(mapping["chat_id"]),
        "bot_kind": str(mapping["bot_kind"]),
        "last_choose_at": int(mapping["last_choose_at"]),
        "chosen_pidor": str(mapping["chosen_pidor"]),
        "last_nudge_at": last_nudge,
    }


def _participant_values(
    row: dict,
) -> tuple:
    return tuple(row[name] for name in PARTICIPANT_FIELDS)


def _chat_state_values(
    row: dict,
) -> tuple:
    return tuple(row[name] for name in CHAT_STATE_FIELDS)


def load_sqlite_snapshot() -> dict:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    participants = [
        _row_to_participant(row)
        for row in connection.execute("SELECT * FROM participants").fetchall()
    ]
    chat_state = [
        _row_to_chat_state(row)
        for row in connection.execute("SELECT * FROM chat_state").fetchall()
    ]
    connection.close()
    return {
        "dumped_at": datetime.now().isoformat(timespec="seconds"),
        "participants": participants,
        "chat_state": chat_state,
    }


def load_postgres_snapshot(
    database_url: str,
) -> dict:
    connection = psycopg.connect(
        postgres_dsn(database_url),
        row_factory=dict_row,
        autocommit=True,
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM participants")
        participants = [_row_to_participant(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM chat_state")
        chat_state = [_row_to_chat_state(row) for row in cursor.fetchall()]
    connection.close()
    return {
        "dumped_at": datetime.now().isoformat(timespec="seconds"),
        "participants": participants,
        "chat_state": chat_state,
    }


def write_sqlite_snapshot(
    snapshot: dict,
) -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.executescript(
        """
        DROP TABLE IF EXISTS participants;
        DROP TABLE IF EXISTS chat_state;
        DROP TABLE IF EXISTS schema_meta;
        """
    )
    for statement in split_sql_statements(POSTGRES_SCHEMA):
        connection.execute(statement)
    connection.execute(
        "INSERT INTO schema_meta (id, version) VALUES (1, ?)",
        (SCHEMA_VERSION,),
    )
    placeholders = ", ".join(["?"] * len(PARTICIPANT_FIELDS))
    columns = ", ".join(PARTICIPANT_FIELDS)
    for row in snapshot["participants"]:
        connection.execute(
            f"INSERT INTO participants ({columns}) VALUES ({placeholders})",
            _participant_values(row),
        )
    state_placeholders = ", ".join(["?"] * len(CHAT_STATE_FIELDS))
    state_columns = ", ".join(CHAT_STATE_FIELDS)
    for row in snapshot["chat_state"]:
        connection.execute(
            f"INSERT INTO chat_state ({state_columns}) VALUES ({state_placeholders})",
            _chat_state_values(row),
        )
    connection.commit()
    connection.close()


def write_json_snapshot(
    snapshot: dict,
) -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_postgres_snapshot(
    snapshot: dict,
    database_url: str,
) -> None:
    connection = psycopg.connect(postgres_dsn(database_url), autocommit=True)
    with connection.cursor() as cursor:
        for statement in split_sql_statements(POSTGRES_SCHEMA):
            cursor.execute(statement)
        participant_placeholders = ", ".join(["%s"] * len(PARTICIPANT_FIELDS))
        participant_columns = ", ".join(PARTICIPANT_FIELDS)
        for row in snapshot["participants"]:
            cursor.execute(
                f"""
                INSERT INTO participants ({participant_columns})
                VALUES ({participant_placeholders})
                ON CONFLICT (chat_id, user_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    tg_username = EXCLUDED.tg_username,
                    birthday_date = EXCLUDED.birthday_date,
                    time_joined = EXCLUDED.time_joined,
                    pidor_score = EXCLUDED.pidor_score,
                    extended_score = EXCLUDED.extended_score,
                    choose_starts_classic = EXCLUDED.choose_starts_classic,
                    choose_starts_extended = EXCLUDED.choose_starts_extended,
                    is_admin = EXCLUDED.is_admin
                """,
                _participant_values(row),
            )
        state_placeholders = ", ".join(["%s"] * len(CHAT_STATE_FIELDS))
        state_columns = ", ".join(CHAT_STATE_FIELDS)
        for row in snapshot["chat_state"]:
            cursor.execute(
                f"""
                INSERT INTO chat_state ({state_columns})
                VALUES ({state_placeholders})
                ON CONFLICT (chat_id, bot_kind) DO UPDATE SET
                    last_choose_at = EXCLUDED.last_choose_at,
                    chosen_pidor = EXCLUDED.chosen_pidor,
                    last_nudge_at = EXCLUDED.last_nudge_at
                """,
                _chat_state_values(row),
            )
    connection.close()


def append_dump_log(
    message: str,
) -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    with DUMP_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{stamp} {message}\n")


def seconds_since_last_dump() -> int:
    if not JSON_PATH.exists():
        return 24 * 60 * 60 + 1
    try:
        raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        dumped_at = str(raw["dumped_at"])
        parsed = datetime.fromisoformat(dumped_at)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return 24 * 60 * 60 + 1
    seconds = int((datetime.now() - parsed).total_seconds())
    if seconds < 0:
        return 0
    return seconds
