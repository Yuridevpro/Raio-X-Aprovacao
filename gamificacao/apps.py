# gamificacao/apps.py
from django.apps import AppConfig

class GamificacaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gamificacao'

    def ready(self):
        # Importa os sinais para que eles sejam registrados quando o app iniciar
        import gamificacao.signals