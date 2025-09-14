# pratica/apps.py (ARQUIVO MODIFICADO)

from django.apps import AppConfig

class PraticaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pratica'

    # =======================================================================
    # INÍCIO DA ADIÇÃO: Importa os signals quando o app é carregado
    # =======================================================================
    def ready(self):
        import pratica.signals
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================