# gestao/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    SolicitacaoExclusao, PromocaoSuperuser, DespromocaoSuperuser, 
    ExclusaoSuperuser, LogAtividade, ExclusaoLogPermanente
)

@admin.register(SolicitacaoExclusao)
class SolicitacaoExclusaoAdmin(admin.ModelAdmin):
    list_display = ('usuario_a_ser_excluido', 'solicitado_por', 'status', 'data_solicitacao', 'revisado_por', 'data_revisao')
    list_filter = ('status', 'data_solicitacao')
    search_fields = ('usuario_a_ser_excluido__username', 'solicitado_por__username')
    raw_id_fields = ('usuario_a_ser_excluido', 'solicitado_por', 'revisado_por')
    
@admin.register(PromocaoSuperuser)
class PromocaoSuperuserAdmin(admin.ModelAdmin):
    list_display = ('usuario_alvo', 'solicitado_por', 'status', 'data_solicitacao')
    list_filter = ('status',)
    search_fields = ('usuario_alvo__username', 'solicitado_por__username')
    filter_horizontal = ('aprovado_por',)
    raw_id_fields = ('usuario_alvo', 'solicitado_por')

@admin.register(DespromocaoSuperuser)
class DespromocaoSuperuserAdmin(admin.ModelAdmin):
    list_display = ('usuario_alvo', 'solicitado_por', 'status', 'data_solicitacao')
    list_filter = ('status',)
    search_fields = ('usuario_alvo__username', 'solicitado_por__username')
    filter_horizontal = ('aprovado_por',)
    raw_id_fields = ('usuario_alvo', 'solicitado_por')

@admin.register(ExclusaoSuperuser)
class ExclusaoSuperuserAdmin(admin.ModelAdmin):
    list_display = ('usuario_alvo', 'solicitado_por', 'status', 'data_solicitacao')
    list_filter = ('status',)
    search_fields = ('usuario_alvo__username', 'solicitado_por__username')
    filter_horizontal = ('aprovado_por',)
    raw_id_fields = ('usuario_alvo', 'solicitado_por')

@admin.register(ExclusaoLogPermanente)
class ExclusaoLogPermanenteAdmin(admin.ModelAdmin):
    list_display = ('solicitado_por', 'status', 'data_solicitacao', 'log_ids_count')
    list_filter = ('status',)
    search_fields = ('solicitado_por__username', 'justificativa')
    filter_horizontal = ('aprovado_por',)
    raw_id_fields = ('solicitado_por', 'usuario_alvo')
    
    @admin.display(description='Qtd. de Logs')
    def log_ids_count(self, obj):
        return len(obj.get_log_ids_as_list())

@admin.register(LogAtividade)
class LogAtividadeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'link_para_alvo', 'is_deleted', 'hash_log_curto')
    list_filter = ('acao', 'is_deleted', 'data_criacao')
    search_fields = ('ator__username', 'detalhes')
    
    readonly_fields = ('data_criacao', 'hash_log')
    raw_id_fields = ('ator', 'deleted_by')
    
    def get_queryset(self, request):
        return LogAtividade.all_logs.get_queryset()

    @admin.display(description='Alvo da Ação')
    def link_para_alvo(self, obj):
        if obj.alvo:
            try:
                url = reverse(f'admin:{obj.alvo._meta.app_label}_{obj.alvo._meta.model_name}_change', args=[obj.alvo.pk])
                return format_html('<a href="{}">{}</a>', url, obj.alvo)
            except Exception:
                return f"{obj.alvo} (Link indisponível)"
        return "N/A"
        
    @admin.display(description='Hash (Início)')
    def hash_log_curto(self, obj):
        if obj.hash_log:
            return obj.hash_log[:12] + '...'
        return "N/A"