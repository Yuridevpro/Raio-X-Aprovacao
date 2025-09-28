# simulados/admin.py
from django.contrib import admin
from .models import Simulado, SessaoSimulado, RespostaSimulado

class RespostaSimuladoInline(admin.TabularInline):
    model = RespostaSimulado
    extra = 0
    readonly_fields = ('questao', 'alternativa_selecionada', 'foi_correta')
    can_delete = False

@admin.register(Simulado)
class SimuladoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'is_oficial', 'status', 'dificuldade', 'criado_por', 'data_criacao')
    list_filter = ('is_oficial', 'status', 'dificuldade', 'data_criacao')
    search_fields = ('nome', 'codigo')
    filter_horizontal = ('questoes',)
    raw_id_fields = ('criado_por',)

@admin.register(SessaoSimulado)
class SessaoSimuladoAdmin(admin.ModelAdmin):
    list_display = ('simulado', 'usuario', 'data_inicio', 'data_fim', 'finalizado')
    list_filter = ('finalizado', 'data_inicio')
    search_fields = ('simulado__nome', 'usuario__username')
    raw_id_fields = ('simulado', 'usuario')
    inlines = [RespostaSimuladoInline]