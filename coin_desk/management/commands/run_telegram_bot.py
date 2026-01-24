"""
Django management command to run the Telegram bot with scheduled notifications.

Starts the Telegram bot in polling mode and configures a scheduler
to send daily transaction notifications.
"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management.base import BaseCommand
from zoneinfo import ZoneInfo

from coin_desk.telegram_bot import handlers  # noqa: F401 - registers handlers
from coin_desk.telegram_bot.bot import bot, dp

logger = logging.getLogger('coin_desk')


class Command(BaseCommand):
    """Run Telegram bot with scheduled notifications."""
    
    help = 'Run Telegram bot with scheduled transaction notifications'

    def handle(self, *args, **kwargs):
        """Execute the command."""
        logging.basicConfig(level=logging.INFO)
        asyncio.run(self.main())

    async def main(self):
        """Start bot polling and scheduler."""
        # Get timezone from settings or use default
        tz = ZoneInfo(getattr(settings, 'TIMEZONE', 'Europe/Moscow'))

        # Start scheduler
        scheduler = AsyncIOScheduler(timezone=tz)

        # Import here to avoid circular imports
        from coin_desk.management.commands.notify_about_new_transactions import (
            Command as NotifyCommand
        )
        notify_command = NotifyCommand()

        scheduler.add_job(
            notify_command.notify_about_new_transactions,
            trigger=CronTrigger(hour=12, minute=30, day_of_week="mon-sun"),
            id="daily_notify_job",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(f"Scheduler started (timezone: {tz})")

        # Start Telegram bot polling
        logger.info("Starting Telegram bot polling...")
        await dp.start_polling(bot)
