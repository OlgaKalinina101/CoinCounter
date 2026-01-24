"""
Django management command to fetch bank statements from Tochka Bank.

Retrieves today's transactions and saves them to the database.
"""
import logging
import uuid
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from coin_desk.scripts.bank_fetch import Tochka

logger = logging.getLogger('coin_desk')


class Command(BaseCommand):
    """Fetch bank statements and save to Transaction model."""
    
    help = 'Fetch bank statements from Tochka Bank and save to database'

    def handle(self, *args, **kwargs):
        """Execute the command."""
        tochka = Tochka()
        batch_id = str(uuid.uuid4())
        today = date.today()
        start_date = today.strftime('%Y-%m-%d')
        end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        
        try:
            tochka.fetch_and_save_statements(start_date, end_date, batch_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully fetched and saved bank statements (batch: {batch_id})'
                )
            )
        except Exception as e:
            logger.exception(f'Error fetching bank statements: {e}')
            self.stdout.write(
                self.style.ERROR(f'Error fetching bank statements: {e}')
            )
            raise

