# gestao/urls.py

from django.urls import path
from . import views

app_name = 'gestao'

urlpatterns = [
    # Páginas principais
    path('', views.dashboard_gestao, name='dashboard'),
    path('questoes/', views.listar_questoes_gestao, name='listar_questoes'),
    path('questoes/nova/', views.adicionar_questao, name='adicionar_questao'),
    path('questoes/editar/<int:questao_id>/', views.editar_questao, name='editar_questao'),
    path('questoes/deletar/<int:questao_id>/', views.deletar_questao, name='deletar_questao'),
    
    # Notificações
    path('notificacoes/', views.listar_notificacoes, name='listar_notificacoes'),
    path('notificacoes/questao/<int:questao_id>/acao/', views.notificacao_acao_agrupada, name='notificacao_acao_agrupada'),
    path('notificacoes/acoes-em-massa/', views.notificacoes_acoes_em_massa, name='notificacoes_acoes_em_massa'),
    
    # API (para chamadas JS)
    path('api/adicionar-entidade/', views.adicionar_entidade_simples, name='adicionar_entidade_simples'),
    path('api/adicionar-assunto/', views.adicionar_assunto, name='adicionar_assunto'),
    path('api/visualizar-questao/<int:questao_id>/', views.visualizar_questao_ajax, name='visualizar_questao_ajax'),
]