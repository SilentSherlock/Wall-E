from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
import threading

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


@dataclass(frozen=True)
class MatchResult:
    matched_message_ids: tuple[int, ...]
    reason: str


class ModerationState:
    """SQLite-backed event and violation store used by the moderation engine."""

    def __init__(self, db_path: str | Path = "data/walle.db") -> None:
        self.db_path = Path(db_path)
        if self.db_path != Path(":memory:"):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _initialize_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS message_events (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL,
                    links_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, user_id, message_id)
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_message_events_lookup
                ON message_events (chat_id, user_id, created_at)
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS violations (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, user_id)
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS managed_chats (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )

    @staticmethod
    def fingerprint(text: str) -> str:
        compact = " ".join(text.lower().split())
        return compact.strip()

    @staticmethod
    def extract_links(text: str) -> frozenset[str]:
        normalized_links = {link.lower().rstrip(".,!?\")") for link in URL_PATTERN.findall(text)}
        return frozenset(normalized_links)

    def check_and_store(
        self,
        *,
        chat_id: int,
        user_id: int,
        message_id: int,
        text: str,
        now: datetime,
        window_seconds: int,
    ) -> MatchResult | None:
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        fingerprint = self.fingerprint(text)
        links = self.extract_links(text)
        now_epoch = int(now.timestamp())
        lower_bound_epoch = int((now - timedelta(seconds=window_seconds)).timestamp())

        matched_ids: list[int] = []
        reason: str | None = None

        with self._lock, self._conn:
            self._conn.execute(
                """
                DELETE FROM message_events
                WHERE chat_id = ? AND user_id = ? AND created_at < ?
                """,
                (chat_id, user_id, lower_bound_epoch),
            )

            history_rows = self._conn.execute(
                """
                SELECT message_id, fingerprint, links_json
                FROM message_events
                WHERE chat_id = ? AND user_id = ?
                ORDER BY created_at ASC
                """,
                (chat_id, user_id),
            ).fetchall()

            for row in history_rows:
                stored_links = set(json.loads(row["links_json"]))
                if fingerprint and row["fingerprint"] == fingerprint:
                    matched_ids.append(int(row["message_id"]))
                    reason = "duplicate_content"
                elif links and stored_links.intersection(links):
                    matched_ids.append(int(row["message_id"]))
                    reason = "duplicate_link"

            self._conn.execute(
                """
                INSERT OR REPLACE INTO message_events (
                    chat_id, user_id, message_id, fingerprint, links_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    user_id,
                    message_id,
                    fingerprint,
                    json.dumps(sorted(links)),
                    now_epoch,
                ),
            )

        if not matched_ids:
            return None
        return MatchResult(matched_message_ids=tuple(matched_ids), reason=reason or "duplicate_content")

    def add_violation(self, chat_id: int, user_id: int) -> int:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO violations (chat_id, user_id, count)
                VALUES (?, ?, 1)
                ON CONFLICT(chat_id, user_id)
                DO UPDATE SET count = count + 1
                """,
                (chat_id, user_id),
            )

            row = self._conn.execute(
                "SELECT count FROM violations WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            ).fetchone()

        return int(row["count"]) if row is not None else 0

    def get_violation_count(self, chat_id: int, user_id: int) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT count FROM violations WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            ).fetchone()
        return int(row["count"]) if row is not None else 0

    def add_managed_chat(self, chat_id: int, title: str) -> bool:
        now_epoch = int(datetime.now(tz=timezone.utc).timestamp())
        with self._lock, self._conn:
            inserted = self._conn.execute(
                """
                INSERT OR IGNORE INTO managed_chats (chat_id, title, created_at)
                VALUES (?, ?, ?)
                """,
                (chat_id, title, now_epoch),
            ).rowcount

            self._conn.execute(
                """
                UPDATE managed_chats
                SET title = ?
                WHERE chat_id = ?
                """,
                (title, chat_id),
            )
        return bool(inserted)

    def get_managed_chat_ids(self) -> list[int]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT chat_id FROM managed_chats ORDER BY chat_id ASC"
            ).fetchall()
        return [int(row["chat_id"]) for row in rows]
