"""
Tochka Bank API integration for fetching bank statements.

This module provides the Tochka class for interacting with Tochka Bank's
Open Banking API to retrieve transaction statements and save them to the database.
"""
import logging
import time
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone

from coin_desk.models import (
    Contractor,
    ContractorExpenseMapping,
    ExpenseCategory,
    Transaction
)
from coin_desk.scripts.keywords import CATEGORY_KEYWORDS
from coin_desk.utils.nlp_processor import get_category_matcher

logger = logging.getLogger('coin_desk')


class Tochka:
    """
    Client for Tochka Bank Open Banking API.
    
    Handles authentication and provides methods to create and retrieve
    bank statements for configured accounts.
    """
    
    def __init__(self):
        """Initialize Tochka API client with credentials from settings."""
        self.jwt_token = settings.JWT_TOKEN
        self.client_id = settings.CLIENT_ID
        self.headers = {
            'Authorization': f'Bearer {self.jwt_token}',
            'client_id': self.client_id
        }

    def create_statement(self, account_id: str, start_date: str, end_date: str) -> dict:
        """
        Create a bank statement request.
        
        Args:
            account_id: Account number with BIC (format: account/BIC)
            start_date: Start date in format "YYYY-MM-DD"
            end_date: End date in format "YYYY-MM-DD"
        
        Returns:
            dict: API response with statement ID
        
        Raises:
            Exception: If statement creation fails
        """
        url = 'https://enter.tochka.com/uapi/open-banking/v1.0/statements'
        data = {
            "Data": {
                "Statement": {
                    "accountId": account_id,
                    "startDateTime": start_date,
                    "endDateTime": end_date
                }
            }
        }
        logger.info(
            f"Creating statement for account {account_id} "
            f"from {start_date} to {end_date}"
        )
        request = requests.post(url=url, headers=self.headers, json=data)
        logger.info(f"Status code: {request.status_code}")
        response = request.json()
        logger.info(f"Create statement response: {response}")
        if request.status_code != 200:
            raise Exception(
                f"Failed to create statement for account {account_id}. "
                f"Error: {response}"
            )
        return response


    def get_statement(self, account_id: str, statement_id: str) -> dict:
        """
        Retrieve statement data (polls until ready).
        
        Args:
            account_id: Account number with BIC (format: account/BIC)
            statement_id: Statement identifier
        
        Returns:
            dict: API response with statement data
        
        Raises:
            Exception: If statement fails or times out
        """
        url = (
            f'https://enter.tochka.com/uapi/open-banking/v1.0/'
            f'accounts/{account_id}/statements/{statement_id}'
        )
        status = None
        attempts = 0
        max_attempts = settings.BANK_STATEMENT_MAX_ATTEMPTS

        while status != 'Ready' and attempts < max_attempts:
            request = requests.get(url=url, headers=self.headers)
            response = request.json()
            logger.info(f"Get statement full response: {response}")
            try:
                status = response['Data']['Statement'][0]['status']
            except (KeyError, IndexError) as e:
                logger.error(f"Error accessing status: {e} - Response: {response}")
                raise

            logger.info(
                f"Statement status for {account_id}/{statement_id}: {status}"
            )

            if status == 'Error':
                raise Exception(
                    f'Statement creation failed for account {account_id}. '
                    f'Status: Error'
                )

            time.sleep(1)
            attempts += 1

        if status != 'Ready':
            raise Exception(
                f"Statement for account {account_id} not ready after "
                f"{max_attempts} seconds"
            )

        return response

    def fetch_and_save_statements(
        self,
        start_date: str,
        end_date: str,
        batch_id: str
    ) -> None:
        """
        Fetch statements for all accounts and save transactions to database.
        
        Args:
            start_date: Start date in format "YYYY-MM-DD"
            end_date: End date in format "YYYY-MM-DD"
            batch_id: Unique batch identifier for this fetch operation
        """

        for account in settings.BANK_ACCOUNTS:
            account_id = f"{account}/{settings.BANK_BIC}"
            logger.info(f"Processing account: {account_id}")
            response = self.create_statement(account_id, start_date, end_date)

            try:
                statement_id = response['Data']['Statement']['statementId']
                statement_data = self.get_statement(account_id, statement_id)
                entries = statement_data['Data']['Statement'][0].get('Transaction', [])
                logger.info(f"Found {len(entries)} transactions")

                for transaction in entries:
                    self._save_transaction(transaction, account, batch_id)

            except (KeyError, IndexError) as e:
                logger.error(f"Error accessing statement: {e} - Response structure: {response}")
                raise

    def _save_transaction(
        self,
        transaction_data: dict,
        account: str,
        batch_id: str
    ) -> None:
        """
        Categorize and save a single transaction to database.
        
        Uses NLP-based categorization with lemmatization, synonyms,
        and embedding similarity for intelligent expense category assignment.
        
        Args:
            transaction_data: Transaction data from API response
            account: Account number
            batch_id: Unique batch identifier
        """
        try:
            # Parse date (format: "2025-06-11")
            date_str = transaction_data.get('documentProcessDate', '')
            naive_date = datetime.strptime(date_str, '%Y-%m-%d')
            date = timezone.make_aware(naive_date)

            # Transaction purpose/description
            purpose = transaction_data.get("description", "").strip()

            # Amount
            amount = transaction_data.get("Amount", {}).get("amount", 0)

            # Extract party and agent info based on transaction direction
            direction = transaction_data.get("creditDebitIndicator")
            if direction == "Debit":
                party = transaction_data.get("CreditorParty", {})
                agent = transaction_data.get("CreditorAgent", {})
                account_data = transaction_data.get("CreditorAccount", {})
                debit = amount
                credit = None
            else:
                party = transaction_data.get("DebtorParty", {})
                agent = transaction_data.get("DebtorAgent", {})
                account_data = transaction_data.get("DebtorAccount", {})
                credit = amount
                debit = None

            contractor_inn = party.get("inn", "").strip()
            contractor_bic = agent.get("identification", "").strip()
            contractor_corr_account = agent.get("accountIdentification", "").strip()
            contractor_bank_name = agent.get("name", "").strip()
            contractor_account = account_data.get("identification", "").strip()

            # Check for duplicate transaction
            if Transaction.objects.filter(
                date=date,
                contractor_inn=contractor_inn,
                contractor_bic=contractor_bic,
                purpose=purpose
            ).exists():
                logger.info(f"Duplicate transaction on {date} - skipped")
                return

            # Find or create Contractor (if INN exists)
            contractor = None
            if contractor_inn:
                contractor = Contractor.objects.filter(inn=contractor_inn).first()
                if not contractor:
                    contractor_name = party.get("name", "").strip()
                    contractor = Contractor.objects.create(
                        name=contractor_name or "Unknown contractor",
                        inn=contractor_inn,
                        bic=contractor_bic
                    )
                    logger.info(
                        f"Created new contractor: {contractor.name} "
                        f"(INN: {contractor_inn})"
                    )

            expense_category = None
            category_source = None

            # 1. For incoming transactions (Credit) - use default category
            if direction == "Credit":
                expense_category, _ = ExpenseCategory.objects.get_or_create(
                    name="Выручка"
                )
                category_source = "default"
                logger.info(
                    f"[{batch_id}] Default category assigned: Выручка"
                )

            # 2. For outgoing transactions (Debit) - use advanced NLP algorithm
            elif direction == "Debit":
                logger.info(
                    f"[{batch_id}] Using NLP analysis for category detection"
                )

                # Advanced NLP categorization algorithm:
                # 1. Multi-query (sentence splitting)
                # 2. Lemmatization (pymorphy2)
                # 3. Synonyms (RuWordNet)
                # 4. Vector search (embeddings)
                # 5. Keyword boost (lemma/synonym match bonus)
                # 6. Exact match boost
                matcher = get_category_matcher()
                best_category_name, final_score, boosts = matcher.find_best_category(
                    purpose,
                    CATEGORY_KEYWORDS,
                    threshold=settings.EMBEDDING_SIMILARITY_THRESHOLD
                )

                if best_category_name:
                    expense_category, _ = ExpenseCategory.objects.get_or_create(
                        name=best_category_name
                    )
                    category_source = "nlp"

                    # Log applied boosts
                    boost_info = []
                    if boosts.get('exact_match'):
                        boost_info.append("exact")
                    if boosts.get('lemma_match'):
                        boost_info.append("lemma")
                    if boosts.get('synonym_match'):
                        boost_info.append("synonym")

                    boost_str = (
                        f" [boosts: {', '.join(boost_info)}]" 
                        if boost_info else ""
                    )

                    logger.info(
                        f"[{batch_id}] NLP category detected: "
                        f"{best_category_name} (score={final_score:.3f}){boost_str}"
                    )
                else:
                    # 3. Fallback: try INN mapping if NLP failed
                    if contractor_inn:
                        mapping = ContractorExpenseMapping.objects.filter(
                            inn=contractor_inn
                        ).select_related('expense_category').first()
                        if mapping:
                            expense_category = mapping.expense_category
                            category_source = "map"
                            logger.info(
                                f"[{batch_id}] Category found via INN mapping "
                                f"{contractor_inn}: {expense_category.name}"
                            )
                        else:
                            logger.info(
                                f"[{batch_id}] No category match for INN "
                                f"{contractor_inn}, leaving empty"
                            )
                    else:
                        logger.info(
                            f"[{batch_id}] No category match (no INN), "
                            f"leaving empty"
                        )

            # Save transaction
            Transaction.objects.create(
                batch_id=batch_id,
                date=date,
                account=account,
                contractor=contractor,
                contractor_inn=contractor_inn,
                contractor_bic=contractor_bic,
                contractor_corr_account=contractor_corr_account,
                contractor_bank_name=contractor_bank_name,
                contractor_account=contractor_account,
                debit=debit,
                credit=credit,
                purpose=purpose,
                expense_category=expense_category,
                category_source=category_source
            )
            logger.info(f"Transaction saved for {date}")

        except Exception as e:
            logger.error(f"Error saving transaction: {e}", exc_info=True)

