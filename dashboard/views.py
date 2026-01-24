"""
Dashboard views for CoinCounter.

Provides a simple wrapper around the main dashboard view.
"""
from dashboard.dashboard_transactions import new_dashboard_view


def dashboard_view(request):
    """
    Main dashboard view wrapper.
    
    Delegates to new_dashboard_view for rendering.
    """
    return new_dashboard_view(request)

