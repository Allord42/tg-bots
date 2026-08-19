import sqlite3
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DATABASE_URL, DB_PATH
from shared.database import POSTGRES_SCHEMA, postgres_dsn


def _split_statements(
    script: str,
) -> list[str]:
    statements: list[str] = []
    for raw in script.split(";"):
        statement = raw.strip()
        if statement:
            statements.append(statement)
    return statements


def migrate_sqlite_to_postgres() -> None:
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL is empty")
    if not Path(DB_PATH).exists():
        raise SystemExit(f"SQLite file missing: {DB_PATH}")

    sqlite_conn = sqlite3.connect(DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    participants = sqlite_conn.execute("SELECT * FROM participants").fetchall()
    chat_state = sqlite_conn.execute("SELECT * FROM chat_state").fetchall()
    sqlite_conn.close()

    pg_conn = psycopg.connect(postgres_dsn(DATABASE_URL), autocommit=True)
    with pg_conn.cursor() as cursor:
        for statement in _split_statements(POSTGRES_SCHEMA):
            cursor.execute(statement)
        for row in participants:
            cursor.execute(
                """
                INSERT INTO participants (
                    chat_id, user_id, display_name, tg_username, birthday_date,
                    time_joined, pidor_score, extended_score,
                    choose_starts_classic, choose_starts_extended, is_admin
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
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
                (
                    int(row["chat_id"]),
                    int(row["user_id"]),
                    str(row["display_name"]),
                    str(row["tg_username"]),
                    int(row["birthday_date"]),
                    int(row["time_joined"]),
                    int(row["pidor_score"]),
                    int(row["extended_score"]),
                    int(row["choose_starts_classic"]),
                    int(row["choose_starts_extended"]),
                    int(row["is_admin"]),
                ),
            )
        for row in chat_state:
            cursor.execute(
                """
                INSERT INTO chat_state (
                    chat_id, bot_kind, last_choose_at, chosen_pidor
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (chat_id, bot_kind) DO UPDATE SET
                    last_choose_at = EXCLUDED.last_choose_at,
                    chosen_pidor = EXCLUDED.chosen_pidor
                """,
                (
                    int(row["chat_id"]),
                    str(row["bot_kind"]),
                    int(row["last_choose_at"]),
                    str(row["chosen_pidor"]),
                ),
            )
        cursor.execute("SELECT COUNT(*) FROM participants")
        player_count = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM chat_state")
        state_count = int(cursor.fetchone()[0])
    pg_conn.close()
    print(f"Migrated participants={player_count} chat_state={state_count}")


if __name__ == "__main__":
    migrate_sqlite_to_postgres()
