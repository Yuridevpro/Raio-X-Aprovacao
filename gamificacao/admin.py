# gamificacao/admin.py (NOVO ARQUIVO)

from django.contrib import admin
from .models import ProfileStreak, Conquista, ConquistaUsuario

@admin.register(Conquista)
class ConquistaAdmin(admin.ModelAdmin):
    """ Admin para criar e gerenciar as conquistas disponíveis na plataforma. """
    list_display = ('nome', 'chave', 'descricao', 'icone', 'cor')
    search_fields = ('nome', 'chave', 'descricao')
    list_filter = ('cor',)
    ordering = ('nome',)
    
    # Preenche o campo 'chave' automaticamente com base no 'nome' (sugestão)
    prepopulated_fields = {'chave': ('nome',)}

@admin.register(ProfileStreak)
class ProfileStreakAdmin(admin.ModelAdmin):
    """
    Admin de apenas leitura para visualizar os dados de streak dos usuários.
    Os dados são atualizados automaticamente via signals.
    """
    list_display = ('user_profile', 'current_streak', 'max_streak', 'last_practice_date')
    search_fields = ('user_profile__user__username',)
    readonly_fields = ('user_profile', 'current_streak', 'max_streak', 'last_practice_date')
    ordering = ('-current_streak',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False # Apenas visualização

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ConquistaUsuario)
class ConquistaUsuarioAdmin(admin.ModelAdmin):
    """ Admin para visualizar quais usuários desbloquearam quais conquistas. """
    list_display = ('user_profile', 'conquista', 'data_conquista')
    list_filter = ('conquista', 'data_conquista')
    search_fields = ('user_profile__user__username', 'conquista__nome')
    readonly_fields = ('user_profile', 'conquista', 'data_conquista')
    
    # raw_id_fields é bom para performance quando há muitos usuários/conquistas
    raw_id_fields = ('user_profile', 'conquista')
    
    ordering = ('-data_conquista',)

    def has_add_permission(self, request):
        return False

# gamificacao/admin.py

from django.contrib import admin
from .models import GamificationSettings

@admin.register(GamificationSettings)
class GamificationSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for the singleton GamificationSettings model.
    """
    list_display = (
        'xp_por_acerto', 
        'xp_por_erro', 
        'xp_bonus_meta_diaria', 
        'meta_diaria_questoes',
        'acertos_consecutivos_para_bonus'
    )

    # Impede que os administradores criem novas instâncias,
    # já que este é um modelo singleton (só pode haver uma configuração).
    def has_add_permission(self, request):
        return False

    # Impede que os administradores deletem a única instância.
    def has_delete_permission(self, request, obj=None):
        return False