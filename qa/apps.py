from django.apps import AppConfig


class QaConfig(AppConfig):
    # Registered in settings.py as 'qa.apps.QaConfig'.
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'qa'
    verbose_name = 'Questions & Answers'
