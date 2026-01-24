"""
Django admin configuration for coin_desk models.

Registers all models with customized admin interfaces.
"""
from django.contrib import admin

from coin_desk.models import (
    Contractor, PLEntry, ExpenseCategory, Transaction, Deal, 
    ContractorExpenseMapping, Lead, LeadAndDealHistory
)

admin.site.register(Contractor)
admin.site.register(PLEntry)
admin.site.register(ExpenseCategory)
admin.site.register(Deal)
admin.site.register(Lead)
admin.site.register(ContractorExpenseMapping)
admin.site.register(LeadAndDealHistory)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date", "contractor", "contractor_inn", "contractor_bic",
        "debit", "credit", "purpose", "expense_category", "category_source"
    )
    list_filter = (
        "date",
        "contractor",
        "contractor_inn",
        "contractor_bic",
        "expense_category",
        "category_source",
    )
    search_fields = ("purpose", "contractor__name", "contractor_inn", "contractor_bic")
    date_hierarchy = "date"
