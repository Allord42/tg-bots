import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DB_PATH, DUMP_MIN_INTERVAL_SECONDS, JSON_PATH
from shared.backup import (
    append_dump_log,
    load_postgres_snapshot,
    resolve_database_url,
    seconds_since_last_dump,
    write_json_snapshot,
    write_sqlite_snapshot,
)


def dump_postgres_to_local() -> None:
    age = seconds_since_last_dump()
    if age < DUMP_MIN_INTERVAL_SECONDS:
        message = f"SKIP last dump {age}s ago"
        append_dump_log(message)
        print(message)
        return
    database_url = resolve_database_url()
    if not database_url:
        append_dump_log("FAIL DATABASE_URL missing")
        raise SystemExit("DATABASE_URL missing")
    snapshot = load_postgres_snapshot(database_url)
    write_sqlite_snapshot(snapshot)
    write_json_snapshot(snapshot)
    player_count = len(snapshot["participants"])
    state_count = len(snapshot["chat_state"])
    message = (
        f"OK participants={player_count} chat_state={state_count} "
        f"sqlite={DB_PATH} json={JSON_PATH}"
    )
    append_dump_log(message)
    print(message)


if __name__ == "__main__":
    dump_postgres_to_local()
