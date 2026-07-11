from django.apps import AppConfig


class TtsaAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ttsa_app'
    
    def ready(self):
        import ttsa_app.signals
