"""
Django management command to send Telegram notifications about new transactions.

Finds unnotified transactions and sends summaries to configured Telegram chats.
This is typically called by the scheduled bot or automation scripts.
"""
import asyncio
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand

from coin_desk.models import Transaction
from coin_desk.telegram_bot.bot import bot
from coin_desk.telegram_bot.utils import (
    prepare_summary_data,
    send_telegram_summary_from_data
)

logger = logging.getLogger('coin_desk')


class Command(BaseCommand):
    """Send Telegram notifications about new transactions."""
    
    help = 'Send Telegram notifications about new unnotified transactions'

    def handle(self, *args, **kwargs):
        """Execute the command."""
        asyncio.run(self.notify_about_new_transactions())

    async def notify_about_new_transactions(self) -> None:
        """
        Send notifications about new transactions via Telegram bot.
        
        Retrieves unnotified transactions, prepares summaries,
        and sends to all configured Telegram chat IDs.
        """
        try:
            # Validate token
            if not settings.TELEGRAM_BOT_TOKEN:
                raise ValueError("TELEGRAM_BOT_TOKEN not configured in settings")

            logger.info(f"Sending notifications to chats: {settings.TELEGRAM_CHAT_IDS}")

            # Find latest unnotified batch
            batch = await sync_to_async(
                lambda: Transaction.objects.filter(notified=False)
                .order_by("-date")
                .values_list("batch_id", flat=True)
                .first()
            )()
            
            logger.info(f"Found batch_id: {batch}")

            if not batch:
                for chat_id in settings.TELEGRAM_CHAT_IDS:
                    logger.info(f"Sending 'no transactions' to chat {chat_id}")
                    await bot.send_message(chat_id, "✅ No new transactions.")
                return

            # Prepare summary data
            data = await sync_to_async(prepare_summary_data)(batch)
            logger.info(f"Prepared summary data for batch {batch}")

            # Send to all configured chats
            for chat_id in settings.TELEGRAM_CHAT_IDS:
                try:
                    logger.info(f"Sending summary to chat {chat_id}")
                    await send_telegram_summary_from_data(data, chat_id)
                except Exception as e:
                    logger.warning(
                        f"Failed to send message to chat {chat_id}: {e}"
                    )

            # Mark as notified
            await sync_to_async(
                lambda: Transaction.objects.filter(batch_id=batch).update(
                    notified=True
                )
            )()
            logger.info(f"Marked transactions in batch {batch} as notified")

        except Exception as e:
            logger.exception(f"Error in notify_about_new_transactions: {e}")
            raise
