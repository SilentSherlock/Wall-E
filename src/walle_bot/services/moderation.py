from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from telegram import ChatPermissions, Message, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ..models import BotSettings
from .state import ModerationState

logger = logging.getLogger(__name__)


class ModerationService:
    def __init__(self, settings: BotSettings, state: ModerationState | None = None) -> None:
        self.settings = settings
        self.state = state or ModerationState()

    def should_process(self, update: Update) -> bool:
        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        if message is None or user is None or chat is None:
            return False
        if chat.type not in {"group", "supergroup"}:
            return False
        if self.settings.monitored_chat_ids and chat.id not in self.settings.monitored_chat_ids:
            return False
        if user.id in self.settings.whitelist_user_ids:
            return False
        if user.is_bot:
            return False
        return True

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        chat = update.effective_chat
        user = update.effective_user
        if message is not None and chat is not None and user is not None and chat.type in {"group", "supergroup"}:
            self.state.upsert_user_profile(
                chat_id=chat.id,
                user_id=user.id,
                username=user.username or "",
                full_name=user.full_name or str(user.id),
            )

        if not self.should_process(update):
            return

        assert message is not None and chat is not None and user is not None

        content = message.text or message.caption or ""
        if not content.strip():
            return

        match = self.state.check_and_store(
            chat_id=chat.id,
            user_id=user.id,
            message_id=message.message_id,
            text=content,
            now=message.date.astimezone(timezone.utc),
            window_seconds=self.settings.rules.duplicate_window_seconds,
            duplicate_trigger_count=self.settings.rules.duplicate_trigger_count,
        )

        if match is None:
            return

        await self._handle_violation(
            message=message,
            context=context,
            user_id=user.id,
            full_name=user.full_name,
            matched_ids=match.matched_message_ids,
            reason=match.reason,
        )

    async def _handle_violation(
        self,
        *,
        message: Message,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        full_name: str,
        matched_ids: tuple[int, ...],
        reason: str,
    ) -> None:
        for msg_id in {*matched_ids, message.message_id}:
            try:
                await context.bot.delete_message(chat_id=message.chat_id, message_id=msg_id)
            except BadRequest:
                logger.debug("Failed to delete message %s in chat %s", msg_id, message.chat_id)

        violation_count = self.state.add_violation(message.chat_id, user_id)

        if violation_count >= self.settings.rules.max_violations:
            await context.bot.ban_chat_member(chat_id=message.chat_id, user_id=user_id)
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=(
                    f"{full_name} has been removed for repeated advertising. "
                    f"Violations: {violation_count}."
                ),
            )
            return

        reason_text = "duplicate message" if reason == "duplicate_content" else "duplicate link"
        if violation_count < self.settings.rules.mute_on_violations:
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=(
                    f"Warning to {full_name}: {reason_text} detected. "
                    f"Violation {violation_count}/{self.settings.rules.max_violations}."
                ),
            )
            return

        until_date = datetime.now(tz=timezone.utc) + timedelta(
            seconds=self.settings.rules.mute_duration_seconds
        )
        await context.bot.restrict_chat_member(
            chat_id=message.chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date,
        )

        await context.bot.send_message(
            chat_id=message.chat_id,
            text=(
                f"Warning to {full_name}: {reason_text} detected. "
                f"Muted for {self.settings.rules.mute_duration_seconds // 60} minutes. "
                f"Violation {violation_count}/{self.settings.rules.max_violations}."
            ),
        )
