# gestao/urls.py

from django.urls import path
from . import views

# Damos um 'app_name' para evitar conflitos de nomes de URL com outros apps
app_name = 'gestao'

urlpatterns = [
    # =======================================================================
    # ROTAS DAS PÁGINAS PRINCIPAIS DO PAINEL
    # =======================================================================
    path('', views.dashboard_gestao, name='dashboard'),
    
    # URLs para gerenciar questões (as páginas que o usuário vê)
    path('questoes/', views.listar_questoes_gestao, name='listar_questoes'),
    path('questoes/nova/', views.adicionar_questao, name='adicionar_questao'),
    path('questoes/editar/<int:questao_id>/', views.editar_questao, name='editar_questao'),
    path('questoes/deletar/<int:questao_id>/', views.deletar_questao, name='deletar_questao'),
    
    # =======================================================================
    # ROTAS DA API (PARA CHAMADAS AJAX)
    # =======================================================================
    # Estas URLs não renderizam páginas, apenas recebem e enviam dados (JSON)
    
    # Rota para a view genérica que adiciona Disciplina, Banca e Instituição
    path('api/adicionar-entidade/', views.adicionar_entidade_simples, name='adicionar_entidade_simples'),
    
    # Rota para a view específica que adiciona um Assunto
    path('api/adicionar-assunto/', views.adicionar_assunto, name='adicionar_assunto'),
    
    
    path('notificacoes/', views.listar_notificacoes, name='listar_notificacoes'),
    path('notificacoes/resolver/<int:notificacao_id>/', views.resolver_notificacao, name='resolver_notificacao'),
    path('notificacoes/arquivar/<int:notificacao_id>/', views.arquivar_notificacao, name='arquivar_notificacao'),
    path('notificacoes/desarquivar/<int:notificacao_id>/', views.desarquivar_notificacao, name='desarquivar_notificacao'),

    path('notificacoes/acoes-em-massa/', views.notificacoes_acoes_em_massa, name='notificacoes_acoes_em_massa'),
    path('api/visualizar-questao/<int:questao_id>/', views.visualizar_questao_ajax, name='visualizar_questao_ajax'),

    # =======================================================================
    # A URL abaixo foi REMOVIDA.
    # A view 'get_assuntos_por_disciplina' foi movida para o app 'questoes' 
    # para ser centralizada e reutilizada. O template agora chama a nova URL 
    # {% url 'questoes:get_assuntos_por_disciplina' %}.
    # =======================================================================
    # path('api/get-assuntos/', views.get_assuntos_por_disciplina, name='get_assuntos_por_disciplina'),
]