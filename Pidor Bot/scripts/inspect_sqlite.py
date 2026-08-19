import sqlite3
from pathlib import Path

from config import DB_PATH


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    ]
    print("db", DB_PATH)
    print("exists", Path(DB_PATH).exists())
    print("tables", tables)
    if "participants" in tables:
        print(
            "participants",
            connection.execute("SELECT COUNT(*) FROM participants").fetchone()[0],
        )
        print(
            "chats",
            connection.execute(
                "SELECT COUNT(DISTINCT chat_id) FROM participants"
            ).fetchone()[0],
        )
    if "chat_state" in tables:
        print(
            "chat_state",
            connection.execute("SELECT COUNT(*) FROM chat_state").fetchone()[0],
        )
    connection.close()


if __name__ == "__main__":
    main()
