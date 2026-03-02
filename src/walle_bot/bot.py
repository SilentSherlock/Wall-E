from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .config import load_settings
from .handlers.commands import whoami
from .services.moderation import ModerationService

logger = logging.getLogger(__name__)


async def _moderation_entry(update, context) -> None:
    service: ModerationService = context.application.bot_data["moderation_service"]
    await service.process_message(update, context)


def create_application(config_path: str = "config/settings.yaml") -> Application:
    settings = load_settings(config_path)

    application = Application.builder().token(settings.bot_token).build()
    application.bot_data["moderation_service"] = ModerationService(settings=settings)

    application.add_handler(CommandHandler("whoami", whoami))
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
            _moderation_entry,
        )
    )

    logger.info(
        "Bot initialized with monitored chats=%s and whitelist count=%s",
        sorted(settings.monitored_chat_ids),
        len(settings.whitelist_user_ids),
    )
    return application


def run(config_path: str = "config/settings.yaml") -> None:
    logging.basicConfig(
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s", level=logging.INFO
    )
    application = create_application(config_path)
    application.run_polling(allowed_updates=["message"])
