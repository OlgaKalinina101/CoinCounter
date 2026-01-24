from django.apps import AppConfig


class CoinDeskConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coin_desk'

    def ready(self):
        import dashboard.signals
