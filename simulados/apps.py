# simulados/apps.py

from django.apps import AppConfig

class SimuladosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'simulados'

    # =======================================================================
    # ADIÇÃO: REGISTRA OS SIGNALS QUANDO O APP É CARREGADO
    # =======================================================================
    def ready(self):
        import simulados.signals