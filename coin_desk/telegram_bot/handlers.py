"""
Telegram bot message handlers.

Currently implements a simple echo handler for testing.
"""
from aiogram import types

from .bot import dp


@dp.message()
async def echo(message: types.Message):
    """Echo handler for testing bot connectivity."""
    await message.answer(f"Bot is working! You wrote: {message.text}")
