from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import Application, ContextTypes

from .moderation import ModerationService

logger = logging.getLogger(__name__)
try:
    BEIJING_TZ = ZoneInfo("Asia/Shanghai")
except ZoneInfoNotFoundError:
    BEIJING_TZ = timezone(timedelta(hours=8))


def _build_time_message(now: datetime) -> str:
    return f"每8小时播报：当前北京时间 {now.strftime('%Y-%m-%d %H:%M:%S')}。"


def _build_startup_message(now: datetime) -> str:
    return f"Wall-E机器人已重启，当前北京时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"


def _seconds_until_next_eight_hour_mark(now: datetime) -> int:
    current_block_hour = (now.hour // 8) * 8
    current_block_start = now.replace(
        hour=current_block_hour,
        minute=0,
        second=0,
        microsecond=0,
    )
    next_block_start = current_block_start + timedelta(hours=8)
    return max(1, int((next_block_start - now).total_seconds()))


async def eight_hour_time_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    service: ModerationService = context.application.bot_data["moderation_service"]
    managed_chat_ids = service.state.get_managed_chat_ids()
    if not managed_chat_ids:
        logger.warning("No managed chats registered; skipped 8-hour report.")
        return

    text = _build_time_message(datetime.now(tz=BEIJING_TZ))
    for chat_id in managed_chat_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except (BadRequest, Forbidden, TelegramError):
            logger.exception("Failed to send 8-hour report to chat %s", chat_id)


async def send_startup_notice(application: Application) -> None:
    service: ModerationService = application.bot_data["moderation_service"]
    managed_chat_ids = service.state.get_managed_chat_ids()
    if not managed_chat_ids:
        logger.warning("No managed chats registered; skipped restart notice.")
        return

    text = _build_startup_message(datetime.now(tz=BEIJING_TZ))
    for chat_id in managed_chat_ids:
        try:
            await application.bot.send_message(chat_id=chat_id, text=text)
        except (BadRequest, Forbidden, TelegramError):
            logger.exception("Failed to send restart notice to chat %s", chat_id)


def register_eight_hour_job(application: Application) -> None:
    if application.job_queue is None:
        logger.error(
            "Job queue unavailable. Install dependencies with python-telegram-bot[job-queue]."
        )
        return

    now = datetime.now(tz=BEIJING_TZ)
    first_delay = _seconds_until_next_eight_hour_mark(now)
    application.job_queue.run_repeating(
        eight_hour_time_report,
        interval=28800,
        first=first_delay,
        name="eight_hour_beijing_time_report",
    )
