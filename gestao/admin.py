# gestao/admin.py (VERSÃO COM PERMISSÕES DE DESENVOLVEDOR)

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    SolicitacaoExclusao, 
    PromocaoSuperuser, 
    DespromocaoSuperuser, 
    ExclusaoSuperuser, 
    LogAtividade
)

@admin.register(SolicitacaoExclusao)
class SolicitacaoExclusaoAdmin(admin.ModelAdmin):
    """ Interface Admin para gerenciar solicitações de exclusão de usuários. """
    list_display = (
        'usuario_a_ser_excluido', 
        'solicitado_por', 
        'status', 
        'data_solicitacao', 
        'revisado_por', 
        'data_revisao'
    )
    list_filter = ('status', 'data_solicitacao')
    search_fields = ('usuario_a_ser_excluido__username', 'solicitado_por__username')
    raw_id_fields = ('usuario_a_ser_excluido', 'solicitado_por', 'revisado_por')
    
@admin.register(PromocaoSuperuser)
class PromocaoSuperuserAdmin(admin.ModelAdmin):
    """ Interface Admin para gerenciar solicitações de promoção a superusuário. """
    list_display = ('usuario_alvo', 'solicitado_por', 'status', 'data_solicitacao')
    list_filter = ('status',)
    search_fields = ('usuario_alvo__username', 'solicitado_por__username')
    filter_horizontal = ('aprovado_por',)

@admin.register(DespromocaoSuperuser)
class DespromocaoSuperuserAdmin(admin.ModelAdmin):
    """ Interface Admin para gerenciar solicitações de despromoção de superusuário. """
    list_display = ('usuario_alvo', 'solicitado_por', 'status', 'data_solicitacao')
    list_filter = ('status',)
    search_fields = ('usuario_alvo__username', 'solicitado_por__username')
    filter_horizontal = ('aprovado_por',)

@admin.register(ExclusaoSuperuser)
class ExclusaoSuperuserAdmin(admin.ModelAdmin):
    """ Interface Admin para gerenciar solicitações de exclusão de superusuário. """
    list_display = ('usuario_alvo', 'solicitado_por', 'status', 'data_solicitacao')
    list_filter = ('status',)
    search_fields = ('usuario_alvo__username', 'solicitado_por__username')
    filter_horizontal = ('aprovado_por',)

@admin.register(LogAtividade)
class LogAtividadeAdmin(admin.ModelAdmin):
    """ Interface Admin para auditoria e gerenciamento dos registros de atividade. """
    list_display = ('__str__', 'link_para_alvo', 'is_deleted', 'hash_log_curto')
    list_filter = ('acao', 'is_deleted', 'data_criacao')
    search_fields = ('ator__username', 'detalhes')
    
    # Apenas campos gerenciados pelo sistema são readonly
    readonly_fields = ('data_criacao', 'hash_log')
    raw_id_fields = ('ator', 'deleted_by')
    
    def get_queryset(self, request):
        return LogAtividade.all_logs.get_queryset()

    @admin.display(description='Alvo da Ação')
    def link_para_alvo(self, obj):
        if obj.alvo:
            url = reverse(
                f'admin:{obj.alvo._meta.app_label}_{obj.alvo._meta.model_name}_change', 
                args=[obj.alvo.pk]
            )
            return format_html('<a href="{}">{}</a>', url, obj.alvo)
        return "N/A"
        
    @admin.display(description='Hash (Início)')
    def hash_log_curto(self, obj):
        if obj.hash_log:
            return obj.hash_log[:12] + '...'
        return "N/A"