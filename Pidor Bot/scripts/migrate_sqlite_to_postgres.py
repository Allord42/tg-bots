import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.backup import (
    load_sqlite_snapshot,
    resolve_database_url,
    write_postgres_snapshot,
)


def migrate_sqlite_to_postgres() -> None:
    database_url = resolve_database_url()
    if not database_url:
        raise SystemExit("DATABASE_URL is empty")
    snapshot = load_sqlite_snapshot()
    write_postgres_snapshot(snapshot, database_url)
    print(
        "Migrated participants="
        f"{len(snapshot['participants'])} chat_state={len(snapshot['chat_state'])}"
    )


if __name__ == "__main__":
    migrate_sqlite_to_postgres()
