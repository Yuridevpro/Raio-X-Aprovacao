# pratica/admin.py

from django.contrib import admin
from .models import RespostaUsuario, Comentario, FiltroSalvo, Notificacao # ADICIONADO: Notificacao
from django.urls import reverse
from django.utils.html import format_html

@admin.register(RespostaUsuario)
class RespostaUsuarioAdmin(admin.ModelAdmin):
    """
    Admin View para RespostaUsuario.
    """
    list_display = ('usuario', 'get_questao_codigo', 'foi_correta', 'data_resposta')
    list_filter = ('foi_correta', 'data_resposta', 'questao__disciplina', 'questao__banca')
    search_fields = ('usuario__username', 'questao__codigo', 'questao__enunciado')
    ordering = ('-data_resposta',)
    readonly_fields = ('usuario', 'questao', 'alternativa_selecionada', 'foi_correta', 'data_resposta')
    raw_id_fields = ('usuario', 'questao',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    @admin.display(description='Questão (Código)', ordering='questao__codigo')
    def get_questao_codigo(self, obj):
        return obj.questao.codigo if obj.questao.codigo else f"ID: {obj.questao.id}"

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    """
    Admin View para Comentario.
    """
    list_display = ('usuario', 'get_questao_codigo', 'short_content', 'data_criacao', 'parent')
    list_filter = ('data_criacao', 'usuario')
    search_fields = ('conteudo', 'usuario__username', 'questao__codigo')
    ordering = ('-data_criacao',)
    readonly_fields = ('data_criacao',)
    raw_id_fields = ('usuario', 'questao', 'parent', 'likes')

    @admin.display(description='Questão (Código)', ordering='questao__codigo')
    def get_questao_codigo(self, obj):
        return obj.questao.codigo if obj.questao.codigo else f"ID: {obj.questao.id}"

    @admin.display(description='Conteúdo')
    def short_content(self, obj):
        return (obj.conteudo[:70] + '...') if len(obj.conteudo) > 70 else obj.conteudo

@admin.register(FiltroSalvo)
class FiltroSalvoAdmin(admin.ModelAdmin):
    """
    Admin View para FiltroSalvo.
    """
    list_display = ('usuario', 'nome', 'parametros_url', 'data_criacao')
    list_filter = ('data_criacao', 'usuario')
    search_fields = ('nome', 'parametros_url', 'usuario__username')
    ordering = ('-data_criacao',)
    readonly_fields = ('usuario', 'nome', 'parametros_url', 'data_criacao')
    raw_id_fields = ('usuario',)

    def has_add_permission(self, request):
        return False

# =======================================================================
# INÍCIO: NOVA CLASSE ADMIN PARA GERENCIAR NOTIFICAÇÕES (ADICIONADA)
# =======================================================================
@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    """
    Admin View para Notificacao.
    Permite a moderação completa dos erros reportados.
    """
    list_display = (
        'link_para_questao', 
        'tipo_erro', 
        'status', 
        'usuario_reportou', 
        'data_criacao'
    )
    list_filter = ('status', 'tipo_erro', 'data_criacao')
    search_fields = (
        'questao__codigo', 
        'descricao', 
        'usuario_reportou__username', 
        'resolvido_por__username'
    )
    ordering = ('-data_criacao',)
    
    # Organiza os campos no formulário de edição
    fieldsets = (
        ('Detalhes do Reporte', {
            'fields': ('link_para_questao', 'tipo_erro', 'descricao')
        }),
        ('Status e Moderação', {
            'fields': ('status', 'usuario_reportou', 'resolvido_por', 'data_criacao', 'data_resolucao', 'data_arquivamento')
        }),
    )
    
    # Campos que não podem ser editados diretamente
    readonly_fields = (
        'link_para_questao', 
        'usuario_reportou', 
        'descricao', 
        'data_criacao', 
        'data_resolucao', 
        'data_arquivamento'
    )
    
    # Adiciona ações em massa na barra superior
    actions = ['marcar_como_resolvido', 'marcar_como_arquivado']

    @admin.action(description='Marcar selecionadas como Resolvidas')
    def marcar_como_resolvido(self, request, queryset):
        queryset.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user)
        self.message_user(request, f"{queryset.count()} notificações foram marcadas como resolvidas.")

    @admin.action(description='Marcar selecionadas como Arquivadas')
    def marcar_como_arquivado(self, request, queryset):
        queryset.update(status=Notificacao.Status.ARQUIVADO)
        self.message_user(request, f"{queryset.count()} notificações foram arquivadas.")

    @admin.display(description='Questão', ordering='questao__codigo')
    def link_para_questao(self, obj):
        # Cria um link clicável para a página de edição da questão
        url = reverse('admin:questoes_questao_change', args=[obj.questao.id])
        return format_html('<a href="{}">{}</a>', url, obj.questao.codigo)

    # Impede a criação de notificações pelo admin (elas só devem vir dos usuários)
    def has_add_permission(self, request):
        return False
# =======================================================================
# FIM: NOVA CLASSE ADMIN
# =======================================================================