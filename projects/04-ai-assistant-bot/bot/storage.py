"""SQLite: память диалога и счётчик сообщений за день."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    role       TEXT NOT NULL,          -- user / assistant
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_messages_user ON messages (user_id, id);

CREATE TABLE IF NOT EXISTS usage (
    user_id INTEGER NOT NULL,
    day     TEXT NOT NULL,             -- 2025-01-31
    count   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);
"""


class Storage:
    def __init__(self, path: str):
        self.path = path

    @asynccontextmanager
    async def _connect(self):
        async with aiosqlite.connect(self.path, timeout=10) as conn:
            yield conn

    async def init(self) -> None:
        async with self._connect() as conn:
            await conn.executescript(SCHEMA)

    # ----- память диалога -----

    async def add_message(self, user_id: int, role: str, content: str, keep: int) -> None:
        """Сохраняет реплику и удаляет самые старые, оставляя не больше keep последних."""
        async with self._connect() as conn:
            await conn.execute(
                "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (user_id, role, content, datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            await conn.execute(
                """DELETE FROM messages WHERE user_id = ? AND id NOT IN
                   (SELECT id FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?)""",
                (user_id, user_id, keep),
            )
            await conn.commit()

    async def history(self, user_id: int, limit: int) -> list[dict]:
        """Последние реплики в хронологическом порядке, в формате сообщений для LLM."""
        async with self._connect() as conn:
            cursor = await conn.execute(
                "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            )
            rows = await cursor.fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    async def clear_history(self, user_id: int) -> None:
        async with self._connect() as conn:
            await conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            await conn.commit()

    # ----- лимиты -----

    async def usage(self, user_id: int, day: str) -> int:
        async with self._connect() as conn:
            cursor = await conn.execute("SELECT count FROM usage WHERE user_id = ? AND day = ?", (user_id, day))
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def add_usage(self, user_id: int, day: str) -> None:
        async with self._connect() as conn:
            await conn.execute(
                """INSERT INTO usage (user_id, day, count) VALUES (?, ?, 1)
                   ON CONFLICT (user_id, day) DO UPDATE SET count = count + 1""",
                (user_id, day),
            )
            await conn.commit()
