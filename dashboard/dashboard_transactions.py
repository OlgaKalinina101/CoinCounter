"""
Main dashboard view with financial metrics and analytics.

Generates comprehensive dashboard with revenue, costs, profit margins,
deals, and leads metrics aggregated by month.
"""
import logging
from datetime import datetime

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from coin_desk.models import Deal, Lead, LeadAndDealHistory, Transaction

logger = logging.getLogger('coin_desk')

# Use constants from settings
EXCLUDED_COST_CATEGORIES = settings.EXCLUDED_COST_CATEGORIES


def new_dashboard_view(request) -> HttpResponse:
    """
    Generate dashboard data and render HTML template or return JSON for debugging.
    
    Creates two main data structures:
    - metrics_table: Contains key metrics (revenue, costs, profit, etc.)
    - expenses_table: Contains expense breakdown by category
    
    Args:
        request: HTTP request object
    
    Returns:
        HttpResponse: Rendered dashboard template or JSON response if debug=1
    """
    year = int(request.GET.get("year", datetime.today().year))
    logger.debug(f"Selected year: {year}")
    months = list(range(1, 13))

    # Revenue
    revenue_by_month = Transaction.objects.filter(
        year=year, expense_category__name="Выручка"
    ).values("month").annotate(total=Sum("credit")).order_by("month")
    logger.debug(f"Revenue by month (raw): {list(revenue_by_month)}")
    revenue_dict = {item["month"]: float(item["total"] or 0) for item in revenue_by_month}
    revenue_values = [revenue_dict.get(m, 0) for m in months]

    # Total costs
    total_costs_by_month = Transaction.objects.filter(
        year=year
    ).exclude(
        expense_category__name__in=EXCLUDED_COST_CATEGORIES
    ).exclude(
        expense_category__isnull=True
    ).values("month").annotate(
        total=Sum("debit", filter=Q(debit__isnull=False))
    ).order_by("month")
    logger.debug(f"Costs by month (raw): {list(total_costs_by_month)}")
    total_costs_dict = {item["month"]: float(item["total"] or 0) for item in total_costs_by_month}
    total_costs_values = [total_costs_dict.get(m, 0) for m in months]

    # Profit
    profit_values = [
        float(revenue - cost)
        for revenue, cost in zip(revenue_values, total_costs_values)
    ]

    # Profit margin percentage
    profit_percentage_values = [
        float(profit / revenue * 100 if revenue else 0)
        for revenue, profit in zip(revenue_values, profit_values)
    ]

    # Deals - current data
    deals_by_month = Deal.objects.filter(
        year=year
    ).values("month").annotate(total=Count("id")).order_by("month")
    deals_dict = {item["month"]: int(item["total"] or 0) for item in deals_by_month}

    # Add historical deals data
    historical_deals = LeadAndDealHistory.objects.filter(
        year=year
    ).values("month", "number_of_deals")
    for item in historical_deals:
        deals_dict[item["month"]] = (
            deals_dict.get(item["month"], 0) + item["number_of_deals"]
        )

    deals_values = [deals_dict.get(m, 0) for m in months]

    # Average revenue per deal
    avg_revenue_per_deal = [
        float(revenue / deals if deals else 0)
        for revenue, deals in zip(revenue_values, deals_values)
    ]

    # Average cost per deal
    avg_cost_per_deal = [
        float(cost / deals if deals else 0)
        for cost, deals in zip(total_costs_values, deals_values)
    ]

    # Leads - current data
    leads_by_month = Lead.objects.filter(
        year=year
    ).values("month").annotate(total=Count("id")).order_by("month")
    leads_dict = {item["month"]: int(item["total"] or 0) for item in leads_by_month}

    # Add historical leads data
    historical_leads = LeadAndDealHistory.objects.filter(
        year=year
    ).values("month", "number_of_leads")
    for item in historical_leads:
        leads_dict[item["month"]] = (
            leads_dict.get(item["month"], 0) + item["number_of_leads"]
        )

    leads_values = [leads_dict.get(m, 0) for m in months]

    # Leads per closed deal
    leads_per_deal = [
        float(leads / deals if deals else 0)
        for leads, deals in zip(leads_values, deals_values)
    ]

    # Expenses by category
    cost_categories = Transaction.objects.filter(
        year=year
    ).exclude(
        expense_category__name__in=EXCLUDED_COST_CATEGORIES
    ).values("expense_category__name").distinct().order_by("expense_category__name")
    logger.debug(f"Cost categories: {list(cost_categories)}")

    expense_rows = []
    for category in cost_categories:
        category_name = category["expense_category__name"]
        costs_by_month = Transaction.objects.filter(
            year=year, 
            expense_category__name=category_name
        ).values("month").annotate(total=Sum("debit")).order_by("month")
        costs_dict = {item["month"]: float(item["total"] or 0) for item in costs_by_month}
        costs_values = [costs_dict.get(m, 0) for m in months]
        expense_rows.append({"label": category_name, "values": costs_values})
        logger.debug(f"Category {category_name}: values={costs_values}")

    metrics_table = {
        "labels": months,
        "rows": [
            {"label": "Выручка", "values": revenue_values},
            {"label": "Себестоимость", "values": total_costs_values},
            {"label": "Прибыль", "values": profit_values},
            {"label": "Прибыль %", "values": profit_percentage_values},
            {"label": "Сделки", "values": deals_values},
            {"label": "Средняя выручка по сделке", "values": avg_revenue_per_deal},
            {"label": "Средняя себестоимость по сделке", "values": avg_cost_per_deal},
            {"label": "Лиды", "values": leads_values},
            {"label": "Лидов на сделку", "values": leads_per_deal},
        ],
    }
    logger.debug(f"Metrics table: {metrics_table}")

    expenses_table = {
        "labels": months,
        "rows": expense_rows,
    }
    logger.debug(f"Expenses table: {expenses_table}")

    context = {
        "year": year,
        "metrics_table": metrics_table,
        "expenses_table": expenses_table,
    }
    if request.GET.get('debug'):
        return JsonResponse(context)
    return render(request, "dashboard/dashboard.html", context)