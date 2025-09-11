# gestao/apps.py

from django.apps import AppConfig

class GestaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestao'

    def ready(self):
        """
        Importa os signals quando a aplicação está pronta.
        """
        import gestao.signals