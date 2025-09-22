# gamificacao/admin.py (ARQUIVO COMPLETO E REFATORADO)

from django.contrib import admin

# =======================================================================
# 1. IMPORTAÇÕES CORRIGIDAS
# Removemos os modelos obsoletos (como TipoCondicao) e adicionamos os novos.
# =======================================================================
from .models import (
    # Modelos de Configuração e Dados do Usuário
    GamificationSettings, ProfileGamificacao, ProfileStreak, MetaDiariaUsuario,
    RankingSemanal, RankingMensal,
    
    # Modelos de Recompensas e Itens
    Avatar, Borda, Banner, TipoDesbloqueio,
    RecompensaPendente, AvatarUsuario, BordaUsuario, BannerUsuario, RecompensaUsuario,
    
    # Modelos de Trilhas, Conquistas e a NOVA arquitetura de Condições
    TrilhaDeConquistas, VariavelDoJogo, Conquista, Condicao, ConquistaUsuario,
    
    # Modelos de Campanhas e Eventos
    Campanha, CampanhaUsuarioCompletion,
)

# =======================================================================
# 2. NOVO INLINE PARA O MODELO DE CONDIÇÃO GENÉRICO
# =======================================================================
class CondicaoInline(admin.TabularInline):
    model = Condicao
    extra = 1 # Permite adicionar uma nova condição em branco
    autocomplete_fields = ['variavel'] # Facilita a busca de variáveis

# =======================================================================
# 3. ADMIN PARA TRILHAS, CONQUISTAS E VARIÁVEIS
# =======================================================================
@admin.register(TrilhaDeConquistas)
class TrilhaDeConquistasAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ordem', 'descricao')
    search_fields = ('nome',)

@admin.register(VariavelDoJogo)
class VariavelDoJogoAdmin(admin.ModelAdmin):
    """
    NOVA INTERFACE: Permite ao super-admin gerenciar as variáveis
    disponíveis para o motor de regras. Substitui o antigo TipoCondicaoAdmin.
    """
    list_display = ('nome_exibicao', 'chave', 'descricao')
    search_fields = ('nome_exibicao', 'chave')

@admin.register(Conquista)
class ConquistaAdmin(admin.ModelAdmin):
    """
    ATUALIZADO: Agora usa o novo CondicaoInline.
    """
    list_display = ('nome', 'trilha', 'is_secreta')
    list_filter = ('trilha', 'is_secreta')
    search_fields = ('nome', 'descricao')
    filter_horizontal = ('pre_requisitos',)
    
    # Usa o novo inline genérico
    inlines = [CondicaoInline]
    
    fieldsets = (
        ('Informações Gerais', {'fields': ('nome', 'descricao', 'trilha', 'icone', 'cor', 'is_secreta')}),
        ('Hierarquia e Requisitos', {'fields': ('pre_requisitos',)}),
        ('Recompensas Diretas (JSON)', {'classes': ('collapse',), 'fields': ('recompensas',)}),
    )

# =======================================================================
# 4. ADMINS PARA RECOMPENSAS (AVATAR, BORDA, BANNER) - Sem alterações
# =======================================================================
class RecompensaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'display_tipos_desbloqueio', 'raridade', 'preco_moedas')
    list_filter = ('raridade', 'tipos_desbloqueio')
    search_fields = ('nome',)
    filter_horizontal = ('tipos_desbloqueio',)

    @admin.display(description='Formas de Desbloqueio')
    def display_tipos_desbloqueio(self, obj):
        return ", ".join([tipo.get_nome_display() for tipo in obj.tipos_desbloqueio.all()])

@admin.register(Avatar)
class AvatarAdmin(RecompensaAdmin):
    pass

@admin.register(Borda)
class BordaAdmin(RecompensaAdmin):
    pass

@admin.register(Banner)
class BannerAdmin(RecompensaAdmin):
    pass

# =======================================================================
# 5. ADMIN PARA CAMPANHAS E REGISTRO DE OUTROS MODELOS - Sem alterações
# =======================================================================
@admin.register(Campanha)
class CampanhaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'gatilho', 'tipo_recorrencia', 'ativo', 'data_inicio', 'data_fim')
    list_filter = ('ativo', 'gatilho', 'tipo_recorrencia')
    search_fields = ('nome',)

# Registro dos outros modelos com a visualização padrão
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
admin.site.register(TipoDesbloqueio)
admin.site.register(Condicao)