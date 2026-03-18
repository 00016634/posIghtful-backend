from django.apps import AppConfig


class BonusesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bonuses'

    def ready(self):
        import bonuses.signals  # noqa: F401
