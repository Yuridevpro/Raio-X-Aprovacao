# gamificacao/admin.py (ARQUIVO COMPLETO E CORRIGIDO)

from django.contrib import admin
from .models import (
    GamificationSettings, ProfileGamificacao, ProfileStreak, MetaDiariaUsuario,
    RankingSemanal, RankingMensal, TrilhaDeConquistas, Conquista, ConquistaUsuario,
    Campanha, CampanhaUsuarioCompletion, Avatar, Borda, Banner,
    RecompensaPendente, AvatarUsuario, BordaUsuario, BannerUsuario,
    TipoCondicao, Condicao  # Importando os modelos corretos
)

# =======================================================================
# INLINE PARA CONDIÇÕES (AGORA USANDO TabularInline PADRÃO)
# =======================================================================
class CondicaoInline(admin.TabularInline):
    model = Condicao
    extra = 1
    verbose_name = "Condição de Desbloqueio"
    verbose_name_plural = "Condições de Desbloqueio"

# =======================================================================
# ADMIN PARA TRILHAS E CONQUISTAS
# =======================================================================
@admin.register(TrilhaDeConquistas)
class TrilhaDeConquistasAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ordem', 'descricao')
    search_fields = ('nome',)

@admin.register(Conquista)
class ConquistaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'trilha', 'is_secreta')
    list_filter = ('trilha', 'is_secreta')
    search_fields = ('nome', 'descricao')
    filter_horizontal = ('pre_requisitos',)
    
    # Usa o novo Inline concreto
    inlines = [CondicaoInline] 
    
    fieldsets = (
        ('Informações Gerais', {'fields': ('nome', 'descricao', 'trilha', 'icone', 'cor', 'is_secreta')}),
        ('Hierarquia', {'fields': ('pre_requisitos',)}),
        ('Recompensas Diretas (JSON)', {'classes': ('collapse',), 'fields': ('recompensas',)}),
    )

# =======================================================================
# ADMIN PARA CAMPANHAS E RECOMPENSAS
# =======================================================================
@admin.register(Campanha)
class CampanhaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'gatilho', 'tipo_recorrencia', 'ativo', 'data_inicio', 'data_fim')
    list_filter = ('ativo', 'gatilho', 'tipo_recorrencia')
    search_fields = ('nome',)

@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_desbloqueio', 'raridade', 'preco_moedas')
    list_filter = ('tipo_desbloqueio', 'raridade'); search_fields = ('nome',)

@admin.register(Borda)
class BordaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_desbloqueio', 'raridade', 'preco_moedas')
    list_filter = ('tipo_desbloqueio', 'raridade'); search_fields = ('nome',)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_desbloqueio', 'raridade', 'preco_moedas')
    list_filter = ('tipo_desbloqueio', 'raridade'); search_fields = ('nome',)
    
@admin.register(TipoCondicao)
class TipoCondicaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'chave', 'descricao')
    search_fields = ('nome', 'chave')

# =======================================================================
# REGISTRO DOS OUTROS MODELOS
# =======================================================================
admin.site.register(GamificationSettings)
admin.site.register(ProfileGamificacao)
admin.site.register(ProfileStreak)
admin.site.register(MetaDiariaUsuario)
admin.site.register(RankingSemanal)
admin.site.register(RankingMensal)
admin.site.register(ConquistaUsuario)
admin.site.register(CampanhaUsuarioCompletion)
admin.site.register(RecompensaPendente)
admin.site.register(AvatarUsuario)
admin.site.register(BordaUsuario)
admin.site.register(BannerUsuario)