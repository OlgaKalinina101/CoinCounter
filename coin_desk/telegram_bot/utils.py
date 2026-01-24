"""
Telegram notification utilities for transaction summaries.

Provides functions to prepare and send transaction summary messages
to Telegram chats.
"""
from django.conf import settings
from django.db.models import Sum

from coin_desk.models import Transaction
from coin_desk.telegram_bot.bot import bot


async def send_telegram_summary_from_data(data: dict, chat_id: int):
    """
    Send formatted transaction summary to Telegram chat.
    
    Args:
        data: Summary data prepared by prepare_summary_data()
        chat_id: Telegram chat ID to send message to
    """
    if data["empty"]:
        await bot.send_message(chat_id, "⚠️ За период выгрузки не найдено ни одной транзакции.")
        return

    credit_lines = [
        f"• {row['contractor__name'] or 'Контрагент не сохранен'}: {row['total']:,}"
        for row in data["credit_details"]
    ]

    debit_lines = [
        f"• {row['contractor__name'] or 'Контрагент не сохранен'}: {row['total']:,}"
        for row in data["debit_details"]
    ]

    nlp_lines = [
        f"• {row.contractor.name if row.contractor else 'Контрагент не сохранен'}: "
        f"{row.debit or row.credit:,} → "
        f"{row.expense_category.name if row.expense_category else '❓'}"
        for row in data["nlp_rows"]
    ]

    uncategorized_debit_lines = [
        f"• {row['contractor__name'] or 'Контрагент не сохранен'}: {row['total']:,}"
        for row in data["uncategorized_debit_details"]
    ]

    message_lines = [
        "✅ Выписки загружены.",
        f"💰 Поступило: {data['credit_total']:,.0f}",
        *credit_lines,
        "",
        f"💸 Потрачено: {data['debit_total']:,.0f}",
        *debit_lines,
    ]

    if nlp_lines:
        message_lines += ["", "🧠 NLP-категоризация:", *nlp_lines]

    if uncategorized_debit_lines:
        message_lines += ["", "⚠️ Категория не определена:", *uncategorized_debit_lines]

    await bot.send_message(chat_id, "\n".join(message_lines))


def prepare_summary_data(batch_id: str) -> dict:
    """
    Prepare transaction summary data for a batch.
    
    Aggregates credits, debits, and categorization info for transactions
    in the specified batch, excluding internal transfers and ignored categories.
    
    Args:
        batch_id: Batch identifier to filter transactions
    
    Returns:
        dict: Summary data with totals, details, and categorization info
    """
    transactions = (
        Transaction.objects
        .filter(batch_id=batch_id)
        .select_related("contractor", "expense_category")
    )

    if not transactions.exists():
        return {"empty": True}

    # Use excluded categories from settings
    exclude_categories = settings.EXCLUDED_COST_CATEGORIES

    # Filter base querysets
    exclude_filter = {"expense_category__name__in": exclude_categories}
    credits = transactions.filter(credit__isnull=False).exclude(**exclude_filter)
    debits = transactions.filter(debit__isnull=False).exclude(**exclude_filter)

    # Aggregate totals
    credit_total = credits.aggregate(total=Sum("credit"))["total"] or 0
    debit_total = debits.aggregate(total=Sum("debit"))["total"] or 0

    # Aggregate by contractor
    credit_details = credits.values("contractor__name").annotate(
        total=Sum("credit")
    )
    debit_details = debits.values("contractor__name").annotate(
        total=Sum("debit")
    )

    # Get NLP-categorized transactions
    nlp_rows = transactions.filter(category_source="nlp")

    # Get uncategorized debit transactions
    uncategorized_debit_details = transactions.filter(
        debit__isnull=False,
        expense_category__isnull=True
    ).values("contractor__name").annotate(total=Sum("debit"))

    return {
        "credit_total": credit_total,
        "debit_total": debit_total,
        "credit_details": list(credit_details),
        "debit_details": list(debit_details),
        "nlp_rows": list(nlp_rows),
        "uncategorized_debit_details": list(uncategorized_debit_details),
        "empty": False,
    }

