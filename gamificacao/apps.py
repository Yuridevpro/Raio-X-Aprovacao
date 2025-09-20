# gamificacao/apps.py (NOVO ARQUIVO)

from django.apps import AppConfig

class GamificacaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gamificacao'
    verbose_name = 'Gamificação' # Nome amigável que aparecerá no admin