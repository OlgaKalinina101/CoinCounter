"""
Django management command to export transactions to Google Sheets.

Exports unloaded transactions for the current year to Google Sheets,
marks them as unloaded after successful export.
"""
import logging

import gspread
from django.conf import settings
from django.core.management.base import BaseCommand
from gspread.utils import ValueInputOption
from oauth2client.service_account import ServiceAccountCredentials

from coin_desk.models import Transaction

logger = logging.getLogger('coin_desk')


class Command(BaseCommand):
    """Export unloaded transactions to Google Sheets."""
    
    help = 'Export unloaded transactions to Google Sheets'

    def handle(self, *args, **kwargs):
        """Execute the command."""
        # Setup Google Sheets API
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            settings.creds_path, 
            scope
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(settings.GOOGLE_SHEET_ID).worksheet("выписка")

        # Headers
        headers = [
            'batch_id', 'date', 'account', 'contractor', 'contractor_inn',
            'contractor_bic', 'contractor_corr_account', 'contractor_bank_name',
            'contractor_account', 'debit', 'credit', 'purpose',
            'expense_category', 'category_source', 'notified'
        ]

        # Add headers if sheet is empty
        if sheet.row_count == 0 or not sheet.row_values(1):
            sheet.append_row(headers, value_input_option='USER_ENTERED')
            logger.info("Added headers to empty sheet")

        # Get unloaded transactions for current year, sorted by date
        current_year = settings.CURRENT_YEAR
        transactions = Transaction.objects.filter(
            year=current_year, 
            unloaded=False
        ).select_related('contractor', 'expense_category').order_by('date')
        
        count = transactions.count()
        logger.info(
            f"Found {count} unloaded transactions for year {current_year}"
        )

        if not transactions.exists():
            self.stdout.write(
                self.style.WARNING(f'No unloaded transactions for {current_year}')
            )
            return

        # Prepare rows
        rows = []
        transaction_ids = []
        for transaction in transactions:
            rows.append([
                transaction.batch_id or '',
                transaction.date.strftime('%Y-%m-%d %H:%M:%S') if transaction.date else '',
                transaction.account or '',
                transaction.contractor.name if transaction.contractor else '',
                transaction.contractor_inn or '',
                transaction.contractor_bic or '',
                transaction.contractor_corr_account or '',
                transaction.contractor_bank_name or '',
                transaction.contractor_account or '',
                str(transaction.debit) if transaction.debit is not None else '',
                str(transaction.credit) if transaction.credit is not None else '',
                transaction.purpose or '',
                transaction.expense_category.name if transaction.expense_category else '',
                transaction.category_source or '',
                str(transaction.notified),
            ])
            transaction_ids.append(transaction.id)

        # Append rows to sheet
        sheet.append_rows(rows, value_input_option='USER_ENTERED')
        
        # Mark as unloaded
        Transaction.objects.filter(id__in=transaction_ids).update(unloaded=True)
        
        logger.info(
            f"Exported {len(rows)} transactions to Google Sheets for year {current_year}"
        )
        self.stdout.write(
            self.style.SUCCESS(f'Successfully exported {len(rows)} transactions')
        )
