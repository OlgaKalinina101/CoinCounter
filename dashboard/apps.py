"""
Django app configuration for dashboard application.
"""
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Dashboard application configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        """Import signals when app is ready."""
        import dashboard.signals  # noqa: F401
