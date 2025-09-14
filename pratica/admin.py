# pratica/admin.py (VERSÃO COM PERMISSÕES DE DESENVOLVEDOR)

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import RespostaUsuario, Comentario, FiltroSalvo, Notificacao

@admin.register(RespostaUsuario)
class RespostaUsuarioAdmin(admin.ModelAdmin):
    """ Interface Admin para auditar e gerenciar as respostas dos usuários. """
    list_display = ('usuario', 'get_questao_link', 'foi_correta', 'data_resposta')
    list_filter = ('foi_correta', 'data_resposta', 'questao__disciplina')
    search_fields = ('usuario__username', 'questao__codigo')
    raw_id_fields = ('usuario', 'questao',)
    
    @admin.display(description='Questão', ordering='questao__codigo')
    def get_questao_link(self, obj):
        if obj.questao:
            url = reverse('admin:questoes_questao_change', args=[obj.questao.id])
            return format_html('<a href="{}">{}</a>', url, obj.questao.codigo)
        return "N/A"

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    """ Interface Admin para auditar e gerenciar os comentários dos usuários. """
    list_display = ('usuario', 'get_questao_link', 'short_content', 'data_criacao', 'parent')
    list_filter = ('data_criacao',)
    search_fields = ('conteudo', 'usuario__username', 'questao__codigo')
    raw_id_fields = ('usuario', 'questao', 'parent', 'likes')
    
    @admin.display(description='Questão', ordering='questao__codigo')
    def get_questao_link(self, obj):
        if obj.questao:
            url = reverse('admin:questoes_questao_change', args=[obj.questao.id])
            return format_html('<a href="{}">{}</a>', url, obj.questao.codigo)
        return "N/A"
        
    @admin.display(description='Comentário')
    def short_content(self, obj):
        return (obj.conteudo[:50] + '...') if len(obj.conteudo) > 50 else obj.conteudo

@admin.register(FiltroSalvo)
class FiltroSalvoAdmin(admin.ModelAdmin):
    """ Interface Admin para gerenciar os filtros salvos pelos usuários. """
    list_display = ('usuario', 'nome', 'data_criacao')
    search_fields = ('nome', 'usuario__username')
    # readonly_fields removidos para permitir edição pelo desenvolvedor.

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    """
    Interface Admin para auditar e gerenciar Notificações e Denúncias.
    Permite edição completa para o desenvolvedor.
    """
    list_display = ('link_para_alvo', 'tipo_erro', 'status', 'usuario_reportou', 'data_criacao')
    list_filter = ('status', 'tipo_erro', 'content_type', 'data_criacao')
    search_fields = ('descricao', 'usuario_reportou__username', 'object_id')
    
    # Os campos abaixo são definidos como apenas leitura pois são gerenciados pelo sistema
    readonly_fields = ('data_criacao', 'data_resolucao')
    raw_id_fields = ('usuario_reportou', 'resolvido_por')

    @admin.display(description='Alvo da Notificação', ordering='object_id')
    def link_para_alvo(self, obj):
        if obj.alvo:
            app_label = obj.content_type.app_label
            model_name = obj.content_type.model
            try:
                url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.alvo.id])
                return format_html('<a href="{}">{}</a>', url, obj.alvo)
            except:
                 return f"{obj.alvo} (Link não disponível)"
        return "Alvo não encontrado"