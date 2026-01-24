"""
Django models for coin_desk application.

This module defines models for:
- Contractors and their expense mappings
- Bank transactions and expense categories
- CRM integration (Deals and Leads from Bitrix24)
- Historical data for leads and deals
"""
from django.db import models

class Contractor(models.Model):
    """Контрагент - организация или ИП"""
    name = models.CharField(max_length=100, verbose_name="Название")
    inn = models.CharField(
        max_length=20, 
        unique=False, 
        blank=True, 
        null=True,
        db_index=True,  # Индекс для быстрого поиска по ИНН
        verbose_name="ИНН"
    )
    bic = models.CharField(max_length=9, blank=True, verbose_name="БИК")
    
    class Meta:
        verbose_name = "Контрагент"
        verbose_name_plural = "Контрагенты"
        ordering = ['name']

    def __str__(self):
        return self.name


class PLEntry(models.Model):
    """Profit & Loss entries (P&L groups for financial reporting)."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Название группы")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "PL Entry"
        verbose_name_plural = "PL Entries"

class ExpenseCategory(models.Model):
    """Expense categories for transaction classification."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    pl_entry = models.ForeignKey(
        PLEntry, 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE, 
        related_name="categories",
        verbose_name="Группа PL"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"

class ContractorExpenseMapping(models.Model):
    """Maps contractor INN to expense categories for automatic transaction classification."""
    inn = models.CharField(max_length=20, unique=True, verbose_name="ИНН контрагента")
    expense_category = models.ForeignKey(
        'ExpenseCategory',
        on_delete=models.CASCADE,
        related_name="inn_mappings",
        verbose_name="Категория расходов"
    )
    description = models.TextField(blank=True, verbose_name="Описание")

    def __str__(self):
        return f"{self.inn} -> {self.expense_category.name}"

    class Meta:
        verbose_name = "Contractor Expense Mapping"
        verbose_name_plural = "Contractor Expense Mappings"

class Transaction(models.Model):
    """Банковская выписка"""
    CATEGORY_SOURCE_CHOICES = [
        ("map", "По ИНН"),
        ("default", "По умолчанию (выручка)"),
        ("embedding", "По эмбеддингам"),
    ]

    batch_id = models.CharField(max_length=36, blank=True, null=True, db_index=True)
    date = models.DateTimeField(db_index=True, verbose_name="Дата операции")
    month = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Месяц")
    year = models.PositiveIntegerField(null=True, blank=True, verbose_name="Год")
    account = models.CharField(max_length=20, verbose_name="Счёт")
    contractor = models.ForeignKey(
        Contractor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Контрагент"
    )
    contractor_inn = models.CharField(max_length=20, blank=True, verbose_name="ИНН контрагента")
    contractor_bic = models.CharField(max_length=9, blank=True, verbose_name="БИК банка")
    contractor_corr_account = models.CharField(max_length=20, blank=True, verbose_name="Корр.счёт")
    contractor_bank_name = models.CharField(max_length=100, blank=True, verbose_name="Наименование банка")
    contractor_account = models.CharField(max_length=20, blank=True, verbose_name="Счёт контрагента")
    debit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Списание"
    )
    credit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Зачисление"
    )
    purpose = models.TextField(blank=True, verbose_name="Назначение платежа")
    expense_category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="transactions",
        verbose_name="Категория расходов"
    )
    category_source = models.CharField(
        max_length=10,
        choices=CATEGORY_SOURCE_CHOICES,
        null=True,
        blank=True,
        default=None,
        verbose_name="Источник категории"
    )
    notified = models.BooleanField(default=False, db_index=True, verbose_name="Уведомлено")
    unloaded = models.BooleanField(default=False, db_index=True, verbose_name="Выгружено")

    def save(self, *args, **kwargs):
        """Override save to automatically populate month and year from date."""
        if self.date:
            self.month = self.date.month
            self.year = self.date.year
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d')} - {self.contractor or 'Без контрагента'}"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ['-date']  # Сортировка по дате (новые сверху)
        indexes = [
            models.Index(fields=['date', 'contractor'], name='trx_date_contractor_idx'),
            models.Index(fields=['year', 'month'], name='trx_year_month_idx'),
            models.Index(fields=['batch_id'], name='trx_batch_idx'),
            models.Index(fields=['notified', 'unloaded'], name='trx_status_idx'),
        ]

class Deal(models.Model):
    """Сделка из Битрикс24"""
    deal_id = models.CharField(max_length=50, unique=True, verbose_name="ID сделки")
    stage_id = models.CharField(max_length=50, verbose_name="Статус")
    month = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Месяц")
    year = models.PositiveIntegerField(null=True, blank=True, verbose_name="Год")
    date_modify = models.DateTimeField(blank=True, null=True, verbose_name="Дата изменения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Сделка"
        verbose_name_plural = "Сделки"
        ordering = ['-date_modify']
        indexes = [
            models.Index(fields=['year', 'month'], name='deal_year_month_idx'),
            models.Index(fields=['stage_id'], name='deal_stage_idx'),
            models.Index(fields=['date_modify'], name='deal_date_mod_idx'),
        ]

    def __str__(self):
        return f"Сделка {self.deal_id} ({self.stage_id})"

class Lead(models.Model):
    """Лид из Битрикс24"""
    lead_id = models.CharField(max_length=50, unique=True, verbose_name="ID лида")
    status_id = models.CharField(max_length=50, blank=True, verbose_name="Статус")
    month = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Месяц")
    year = models.PositiveIntegerField(null=True, blank=True, verbose_name="Год")
    date_modify = models.DateTimeField(blank=True, null=True, verbose_name="Дата изменения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Лид"
        verbose_name_plural = "Лиды"
        ordering = ['-date_modify']
        indexes = [
            models.Index(fields=['year', 'month'], name='lead_year_month_idx'),
            models.Index(fields=['status_id'], name='lead_status_idx'),
            models.Index(fields=['date_modify'], name='lead_date_mod_idx'),
        ]

    def __str__(self):
        return f"Лид {self.lead_id} ({self.status_id})"

class LeadAndDealHistory(models.Model):
    """Исторические данные по лидам и сделкам (для старых периодов)"""
    month = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Месяц")
    year = models.PositiveIntegerField(null=True, blank=True, verbose_name="Год")
    number_of_deals = models.PositiveSmallIntegerField(default=0, verbose_name="Количество сделок")
    number_of_leads = models.PositiveSmallIntegerField(default=0, verbose_name="Количество лидов")

    class Meta:
        verbose_name = "История лидов и сделок"
        verbose_name_plural = "История лидов и сделок"
        ordering = ['-year', '-month']
        indexes = [
            models.Index(fields=['year', 'month'], name='hist_year_month_idx'),
        ]
        db_table = 'coin_desk_lead_and_deal_history'  # Сохраняем старое имя таблицы!

    def __str__(self):
        return f"{self.year}-{self.month:02d}: Сделок {self.number_of_deals}, Лидов {self.number_of_leads}"