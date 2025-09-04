# pratica/admin.py

from django.contrib import admin
from .models import RespostaUsuario, Comentario, FiltroSalvo

@admin.register(RespostaUsuario)
class RespostaUsuarioAdmin(admin.ModelAdmin):
    """
    Admin View para RespostaUsuario.
    Configurado como uma visão de "apenas leitura" para garantir a integridade
    dos dados de desempenho do usuário. Um administrador pode ver e filtrar
    as respostas, mas não pode criá-las ou alterá-las por aqui.
    """
    list_display = ('usuario', 'get_questao_codigo', 'foi_correta', 'data_resposta')
    list_filter = ('foi_correta', 'data_resposta', 'questao__disciplina', 'questao__banca')
    search_fields = ('usuario__username', 'questao__codigo', 'questao__enunciado')
    ordering = ('-data_resposta',)
    
    # Define todos os campos como apenas leitura no formulário de edição
    readonly_fields = ('usuario', 'questao', 'alternativa_selecionada', 'foi_correta', 'data_resposta')
    
    # Otimização para ForeignKeys com muitos itens
    raw_id_fields = ('usuario', 'questao',)

    # Impede a criação de novas respostas pelo admin
    def has_add_permission(self, request):
        return False

    # Impede a alteração das respostas pelo admin
    def has_change_permission(self, request, obj=None):
        return True # Permite ver, mas os readonly_fields impedem a edição

    # Opcional: Descomente se quiser impedir a exclusão também
    # def has_delete_permission(self, request, obj=None):
    #     return False

    @admin.display(description='Questão (Código)', ordering='questao__codigo')
    def get_questao_codigo(self, obj):
        return obj.questao.codigo if obj.questao.codigo else f"ID: {obj.questao.id}"

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    """
    Admin View para Comentario.
    Ideal para moderação de comentários.
    """
    list_display = ('usuario', 'get_questao_codigo', 'short_content', 'data_criacao', 'parent')
    list_filter = ('data_criacao', 'usuario')
    search_fields = ('conteudo', 'usuario__username', 'questao__codigo')
    ordering = ('-data_criacao',)
    
    # Campos que não devem ser editáveis
    readonly_fields = ('data_criacao',)
    
    # Otimização para ForeignKeys
    raw_id_fields = ('usuario', 'questao', 'parent', 'likes')

    @admin.display(description='Questão (Código)', ordering='questao__codigo')
    def get_questao_codigo(self, obj):
        return obj.questao.codigo if obj.questao.codigo else f"ID: {obj.questao.id}"

    @admin.display(description='Conteúdo')
    def short_content(self, obj):
        # Mostra apenas os primeiros 70 caracteres do comentário na lista
        return (obj.conteudo[:70] + '...') if len(obj.conteudo) > 70 else obj.conteudo

@admin.register(FiltroSalvo)
class FiltroSalvoAdmin(admin.ModelAdmin):
    """
    Admin View para FiltroSalvo.
    Útil para ver quais filtros os usuários estão salvando e para depuração.
    """
    list_display = ('usuario', 'nome', 'parametros_url', 'data_criacao')
    list_filter = ('data_criacao', 'usuario')
    search_fields = ('nome', 'parametros_url', 'usuario__username')
    ordering = ('-data_criacao',)
    
    readonly_fields = ('usuario', 'nome', 'parametros_url', 'data_criacao')
    raw_id_fields = ('usuario',)

    def has_add_permission(self, request):
        return False