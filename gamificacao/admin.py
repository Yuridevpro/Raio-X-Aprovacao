# gamificacao/admin.py
from django.contrib import admin
from .models import (
    GamificationSettings, ProfileGamificacao, ProfileStreak, MetaDiariaUsuario,
    RankingSemanal, RankingMensal,
    Avatar, Borda, Banner, TipoDesbloqueio,
    RecompensaPendente, AvatarUsuario, BordaUsuario, BannerUsuario, RecompensaUsuario,
    TrilhaDeConquistas, SerieDeConquistas, VariavelDoJogo, Conquista, Condicao, ConquistaUsuario,
    Campanha, CampanhaUsuarioCompletion,
)

class CondicaoInline(admin.TabularInline):
    model = Condicao
    extra = 1
    autocomplete_fields = ['variavel']

@admin.register(TrilhaDeConquistas)
class TrilhaDeConquistasAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ordem', 'descricao')
    search_fields = ('nome',)

@admin.register(SerieDeConquistas)
class SerieDeConquistasAdmin(admin.ModelAdmin):
    list_display = ('nome', 'trilha', 'ordem')
    list_filter = ('trilha',)
    search_fields = ('nome',)
    raw_id_fields = ('trilha',)

@admin.register(VariavelDoJogo)
class VariavelDoJogoAdmin(admin.ModelAdmin):
    list_display = ('nome_exibicao', 'chave', 'descricao')
    search_fields = ('nome_exibicao', 'chave')

@admin.register(Conquista)
class ConquistaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'trilha', 'serie', 'ordem_na_serie', 'is_secreta')
    list_filter = ('trilha', 'serie', 'is_secreta')
    search_fields = ('nome', 'descricao')
    filter_horizontal = ('pre_requisitos',)
    inlines = [CondicaoInline]
    raw_id_fields = ('trilha', 'serie')
    
    fieldsets = (
        ('Informações Gerais', {'fields': ('nome', 'descricao', 'icone', 'cor', 'is_secreta')}),
        ('Hierarquia e Requisitos', {'fields': ('trilha', 'serie', 'pre_requisitos',)}),
        ('Recompensas Diretas (JSON)', {'classes': ('collapse',), 'fields': ('recompensas',)}),
    )

class RecompensaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'display_tipos_desbloqueio', 'raridade', 'preco_moedas')
    list_filter = ('raridade', 'tipos_desbloqueio')
    search_fields = ('nome',)
    filter_horizontal = ('tipos_desbloqueio',)

    @admin.display(description='Formas de Desbloqueio')
    def display_tipos_desbloqueio(self, obj):
        return ", ".join([tipo.get_nome_display() for tipo in obj.tipos_desbloqueio.all()])

@admin.register(Avatar)
class AvatarAdmin(RecompensaAdmin): pass

@admin.register(Borda)
class BordaAdmin(RecompensaAdmin): pass

@admin.register(Banner)
class BannerAdmin(RecompensaAdmin): pass

@admin.register(Campanha)
class CampanhaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'gatilho', 'tipo_recorrencia', 'ativo', 'data_inicio', 'data_fim')
    list_filter = ('ativo', 'gatilho', 'tipo_recorrencia')
    search_fields = ('nome',)
    raw_id_fields = ('simulado_especifico',)

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