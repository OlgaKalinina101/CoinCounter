"""
Custom template filters for dashboard formatting.

Provides filters for number formatting and month name localization.
"""
from django import template

register = template.Library()


@register.filter
def comma_decimal(value):
    """
    Replace decimal point with comma for European number format.
    
    Args:
        value: Number to format
    
    Returns:
        str: Formatted number with comma as decimal separator
    """
    if value is None:
        return ""
    return str(value).replace(".", ",")


@register.filter
def intspace_no_cents(value):
    """
    Format integer with spaces as thousands separator.
    
    Args:
        value: Number to format
    
    Returns:
        str: Formatted number with spaces (e.g., "1 000 000")
    """
    try:
        value = int(float(value))
        return f"{value:,}".replace(",", " ")
    except (ValueError, TypeError):
        return value


@register.filter
def month_name(month):
    """
    Convert month number (1-12) to Russian month name.
    
    Args:
        month: Month number (1-12)
    
    Returns:
        str: Russian month name
    """
    months = {
        1: 'Январь',
        2: 'Февраль',
        3: 'Март',
        4: 'Апрель',
        5: 'Май',
        6: 'Июнь',
        7: 'Июль',
        8: 'Август',
        9: 'Сентябрь',
        10: 'Октябрь',
        11: 'Ноябрь',
        12: 'Декабрь',
    }
    return months.get(int(month), '')


@register.filter
def sum_values(values):
    """
    Sum all numeric values in a list.
    
    Args:
        values: List of numbers
    
    Returns:
        Sum of all values
    """
    try:
        return sum(float(v) for v in values if v)
    except (ValueError, TypeError):
        return 0


@register.filter
def avg_values(values):
    """
    Calculate average of non-zero values in a list.
    
    Args:
        values: List of numbers
    
    Returns:
        Average of non-zero values
    """
    try:
        non_zero = [float(v) for v in values if v]
        return sum(non_zero) / len(non_zero) if non_zero else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
