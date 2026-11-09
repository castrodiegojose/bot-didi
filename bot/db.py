from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bot.textutil import normalize


@dataclass(frozen=True)
class Item:
    name: str
    display_name: str
    added_by: str | None = None


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def close(self) -> None:
        self.conn.close()

    def is_member(self, telegram_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM members WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
        return row is not None

    def authorize(self, telegram_id: int, name: str) -> None:
        self.conn.execute(
            """
            INSERT INTO members (telegram_id, name, authorized_at)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET name = excluded.name
            """,
            (telegram_id, name, _now()),
        )
        self.conn.commit()

    def add(self, displays: list[str], added_by: str) -> tuple[list[Item], list[Item]]:
        added: list[Item] = []
        existing: list[Item] = []
        for display in displays:
            key = normalize(display)
            current = self._pending(key)
            if current is not None:
                existing.append(current)
                continue
            self.conn.execute(
                """
                INSERT INTO items (name, display_name, status, added_by, added_at)
                VALUES (?, ?, 'pending', ?, ?)
                """,
                (key, display, added_by, _now()),
            )
            added.append(Item(key, display, added_by))
        self.conn.commit()
        return added, existing

    def pending(self) -> list[Item]:
        rows = self.conn.execute(
            "SELECT name, display_name, added_by FROM items WHERE status = 'pending' ORDER BY added_at, id"
        ).fetchall()
        return [Item(row["name"], row["display_name"], row["added_by"]) for row in rows]

    def delete(self, displays: list[str]) -> tuple[list[Item], list[str]]:
        deleted: list[Item] = []
        missing: list[str] = []
        for display in displays:
            current = self._pending(normalize(display))
            if current is None:
                missing.append(display)
                continue
            self.conn.execute(
                "DELETE FROM items WHERE status = 'pending' AND name = ?",
                (current.name,),
            )
            deleted.append(current)
        self.conn.commit()
        return deleted, missing

    def buy(self, displays: list[str], bought_by: str) -> tuple[list[Item], list[Item]]:
        marked: list[Item] = []
        created: list[Item] = []
        moment = _now()
        for display in displays:
            key = normalize(display)
            current = self._pending(key)
            if current is not None:
                self._mark(current.name, bought_by, moment)
                marked.append(current)
                continue
            self.conn.execute(
                """
                INSERT INTO items (name, display_name, status, added_by, added_at, bought_by, bought_at)
                VALUES (?, ?, 'bought', ?, ?, ?, ?)
                """,
                (key, display, bought_by, moment, bought_by, moment),
            )
            created.append(Item(key, display, bought_by))
        self.conn.commit()
        return marked, created

    def buy_all(self, bought_by: str) -> list[Item]:
        items = self.pending()
        if not items:
            return []
        moment = _now()
        for item in items:
            self._mark(item.name, bought_by, moment)
        self.conn.commit()
        return items

    def _init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS members (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                authorized_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pending', 'bought')),
                added_by TEXT,
                added_at TEXT NOT NULL,
                bought_by TEXT,
                bought_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_items_pending ON items (status, name);
            """
        )
        self.conn.commit()

    def _pending(self, name: str) -> Item | None:
        row = self.conn.execute(
            """
            SELECT name, display_name, added_by
            FROM items
            WHERE status = 'pending' AND name = ?
            """,
            (name,),
        ).fetchone()
        if row is None:
            return None
        return Item(row["name"], row["display_name"], row["added_by"])

    def _mark(self, name: str, bought_by: str, moment: str) -> None:
        self.conn.execute(
            """
            UPDATE items
            SET status = 'bought', bought_by = ?, bought_at = ?
            WHERE status = 'pending' AND name = ?
            """,
            (bought_by, moment, name),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
