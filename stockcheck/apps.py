from django.apps import AppConfig


class StockcheckConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stockcheck"
    verbose_name = "Random stock checks"
