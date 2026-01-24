"""
Celery tasks for coin_desk application.

Tasks:
- fetch_and_save_statements_task: Fetch bank statements from Tochka bank
- export_new_transactions_to_sheets: Export new transactions to Google Sheets
"""
import logging
import uuid
from datetime import date, timedelta

import gspread
from celery import shared_task
from gspread.utils import ValueInputOption
from oauth2client.service_account import ServiceAccountCredentials

from coin_counter.settings import creds_path, sheet_id
from coin_desk.models import Transaction
from coin_desk.scripts.bank_fetch import Tochka

logger = logging.getLogger('coin_desk')

@shared_task
def fetch_and_save_statements_task():
    """
    Celery task для получения банковских выписок.
    Получает данные за сегодня и сохраняет в БД.
    """
    batch_id = str(uuid.uuid4())
    try:
        tochka = Tochka()
        today = date.today()
        start_date = today.strftime('%Y-%m-%d')
        end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        tochka.fetch_and_save_statements(start_date, end_date, batch_id=batch_id)
        logger.info(f"Successfully fetched statements for {start_date}, batch_id={batch_id}")
    except Exception as e:
        logger.error(f"Error in fetch_and_save_statements: {e}", exc_info=True)


@shared_task
def export_new_transactions_to_sheets():
    """
    Export unloaded transactions to Google Sheets.
    
    Note: This exports ALL transactions and clears the sheet first.
    The unloaded flag is used to track which transactions have been processed.
    """
    logger.info("Starting export of transactions to Google Sheets")

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).worksheet("выписка")

    headers = [
        'batch_id', 'date', 'month', 'year', 'account', 'contractor', 'contractor_inn', 'contractor_bic',
        'contractor_corr_account', 'contractor_bank_name', 'contractor_account',
        'debit', 'credit', 'purpose', 'expense_category', 'category_source', 'notified',
        'unloaded'
    ]

    # Clear sheet before export
    sheet.clear()
    sheet.append_row(headers, value_input_option=ValueInputOption.user_entered)

    # Get ALL transactions (intentionally exports all, not just unloaded=False)
    transactions = Transaction.objects.select_related('contractor', 'expense_category')
    if not transactions.exists():
        logger.info("No transactions to export")
        return

    # Prepare rows and mark as unloaded
    rows = []
    transaction_ids = []
    for transaction in transactions:
        rows.append([
            transaction.batch_id or '',
            transaction.date.strftime('%Y-%m-%d %H:%M:%S') if transaction.date else '',
            transaction.month or '',
            transaction.year or '',
            transaction.account or '',
            str(transaction.contractor) if transaction.contractor else '',
            transaction.contractor_inn or '',
            transaction.contractor_bic or '',
            transaction.contractor_corr_account or '',
            transaction.contractor_bank_name or '',
            transaction.contractor_account or '',
            str(transaction.debit).replace('.', ',') if transaction.debit is not None else '',
            str(transaction.credit).replace('.', ',') if transaction.credit is not None else '',
            transaction.purpose or '',
            str(transaction.expense_category) if transaction.expense_category else '',
            transaction.category_source or '',
            str(transaction.notified),
            str(transaction.unloaded)
        ])
        transaction_ids.append(transaction.id)

    # Export to sheets
    sheet.append_rows(rows, value_input_option=ValueInputOption.user_entered)
    
    # Mark all as unloaded
    Transaction.objects.filter(id__in=transaction_ids).update(unloaded=True)

    logger.info(f"Exported {len(rows)} transactions to Google Sheets")





