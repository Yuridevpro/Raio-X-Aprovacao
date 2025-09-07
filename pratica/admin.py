# pratica/admin.py

from django.contrib import admin
from .models import RespostaUsuario, Comentario, FiltroSalvo, Notificacao
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone

# =======================================================================
# ADMINS PARA MODELOS DE INTERAÇÃO (JÁ CORRETOS)
# =======================================================================

@admin.register(RespostaUsuario)
class RespostaUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'get_questao_codigo', 'foi_correta', 'data_resposta')
    list_filter = ('foi_correta', 'data_resposta', 'questao__disciplina')
    search_fields = ('usuario__username', 'questao__codigo')
    raw_id_fields = ('usuario', 'questao',)
    def get_questao_codigo(self, obj):
        return obj.questao.codigo
    get_questao_codigo.short_description = 'Questão'

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'get_questao_codigo', 'short_content', 'data_criacao')
    search_fields = ('conteudo', 'usuario__username', 'questao__codigo')
    raw_id_fields = ('usuario', 'questao', 'parent', 'likes')
    def get_questao_codigo(self, obj):
        return obj.questao.codigo
    get_questao_codigo.short_description = 'Questão'
    def short_content(self, obj):
        return (obj.conteudo[:50] + '...') if len(obj.conteudo) > 50 else obj.conteudo
    short_content.short_description = 'Comentário'

@admin.register(FiltroSalvo)
class FiltroSalvoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'nome', 'data_criacao')
    search_fields = ('nome', 'usuario__username')
    readonly_fields = ('usuario', 'nome', 'parametros_url', 'data_criacao')


# =======================================================================
# ADMIN PARA NOTIFICAÇÕES (VERSÃO FINAL, SIMPLIFICADA E CORRIGIDA)
# =======================================================================

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    """
    Admin View para o modelo Notificacao, alinhada com o fluxo simplificado.
    """
    list_display = (
        'link_para_questao', 
        'tipo_erro', 
        'status', 
        'usuario_reportou', 
        'data_criacao',
        'resolvido_por' # Adicionado para visibilidade
    )
    list_filter = ('status', 'tipo_erro', 'data_criacao')
    search_fields = ('questao__codigo', 'descricao', 'usuario_reportou__username')
    ordering = ('-data_criacao',)
    
    # Organiza os campos no formulário de detalhes/edição
    fieldsets = (
        ('Detalhes do Reporte', {
            'fields': ('link_para_questao_readonly', 'tipo_erro', 'descricao', 'data_criacao')
        }),
        ('Status da Moderação', {
            # O status pode ser alterado manualmente aqui se necessário
            'fields': ('status', 'usuario_reportou', 'resolvido_por', 'data_resolucao')
        }),
    )
    
    # --- CORREÇÃO PRINCIPAL: REMOÇÃO DE 'data_arquivamento' ---
    readonly_fields = (
        'link_para_questao_readonly', 
        'usuario_reportou', 
        'data_criacao', 
        'data_resolucao', 
        'resolvido_por'
    )

    # --- CORREÇÃO: Ações em massa simplificadas ---
    actions = ['marcar_como_corrigido', 'marcar_como_rejeitado']

    @admin.action(description='Marcar selecionadas como "Corrigido"')
    def marcar_como_corrigido(self, request, queryset):
        # Ação para o status RESOLVIDO (Corrigido)
        updated = queryset.update(
            status=Notificacao.Status.RESOLVIDO, 
            resolvido_por=request.user,
            data_resolucao=timezone.now()
        )
        self.message_user(request, f"{updated} notificações foram marcadas como Corrigidas.")

    @admin.action(description='Marcar selecionadas como "Rejeitado"')
    def marcar_como_rejeitado(self, request, queryset):
        # Ação para o status REJEITADO
        updated = queryset.update(status=Notificacao.Status.REJEITADO)
        self.message_user(request, f"{updated} notificações foram marcadas como Rejeitadas.")

    # Função para criar um link clicável para a questão
    @admin.display(description='Questão', ordering='questao__codigo')
    def link_para_questao(self, obj):
        url = reverse('admin:questoes_questao_change', args=[obj.questao.id])
        return format_html('<a href="{}">{}</a>', url, obj.questao.codigo)

    # Função separada para o campo readonly no fieldset
    @admin.display(description='Questão')
    def link_para_questao_readonly(self, obj):
        return self.link_para_questao(obj)

    # Impede a criação de novas notificações a partir do painel Admin
    def has_add_permission(self, request):
        return False