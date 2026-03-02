from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    if chat.type not in {"group", "supergroup"}:
        await message.reply_text("Bot is running. Add me to a group and use /start there.")
        return

    state = context.application.bot_data["moderation_service"].state
    chat_title = chat.title or str(chat.id)
    created = state.add_managed_chat(chat_id=chat.id, title=chat_title)
    current_time = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if created:
        await message.reply_text(
            f"Registered this group for management.\nChat ID: {chat.id}\nRegistered at: {current_time}"
        )
        return

    await message.reply_text(
        f"This group is already registered.\nChat ID: {chat.id}\nChecked at: {current_time}"
    )


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return

    username = f"@{user.username}" if user.username else "(none)"
    text = (
        "User info\n"
        f"ID: {user.id}\n"
        f"Name: {user.full_name}\n"
        f"Username: {username}\n"
        f"Chat ID: {chat.id}"
    )
    await update.effective_message.reply_text(text)
