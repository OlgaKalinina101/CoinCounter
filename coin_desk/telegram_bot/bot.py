"""
Telegram bot initialization for transaction notifications.

Configures aiogram bot and dispatcher with HTML parsing mode.
"""
import os

import django

# Initialize Django before importing settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coin_counter.settings")
django.setup()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from django.conf import settings

bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())
