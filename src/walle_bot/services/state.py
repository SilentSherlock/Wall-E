from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


@dataclass(frozen=True)
class MessageEvent:
    chat_id: int
    user_id: int
    message_id: int
    fingerprint: str
    links: frozenset[str]
    created_at: datetime


@dataclass(frozen=True)
class MatchResult:
    matched_message_ids: tuple[int, ...]
    reason: str


class ModerationState:
    """In-memory event and violation store used by the moderation engine."""

    def __init__(self) -> None:
        self._events: dict[tuple[int, int], deque[MessageEvent]] = defaultdict(deque)
        self._violations: dict[tuple[int, int], int] = defaultdict(int)

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
        key = (chat_id, user_id)
        history = self._events[key]
        lower_bound = now - timedelta(seconds=window_seconds)

        while history and history[0].created_at < lower_bound:
            history.popleft()

        matched_ids: list[int] = []
        reason: str | None = None
        for event in history:
            if fingerprint and event.fingerprint == fingerprint:
                matched_ids.append(event.message_id)
                reason = "duplicate_content"
            elif links and event.links.intersection(links):
                matched_ids.append(event.message_id)
                reason = "duplicate_link"

        history.append(
            MessageEvent(
                chat_id=chat_id,
                user_id=user_id,
                message_id=message_id,
                fingerprint=fingerprint,
                links=links,
                created_at=now,
            )
        )

        if not matched_ids:
            return None
        return MatchResult(matched_message_ids=tuple(matched_ids), reason=reason or "duplicate_content")

    def add_violation(self, chat_id: int, user_id: int) -> int:
        key = (chat_id, user_id)
        self._violations[key] += 1
        return self._violations[key]

    def get_violation_count(self, chat_id: int, user_id: int) -> int:
        return self._violations[(chat_id, user_id)]
