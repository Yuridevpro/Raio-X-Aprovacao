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
    path('questoes/acoes-em-massa/', views.questoes_acoes_em_massa, name='questoes_acoes_em_massa'),

    # Notificações
    path('notificacoes/', views.listar_notificacoes, name='listar_notificacoes'),
    path('notificacoes/<int:questao_id>/acao-agrupada/', views.notificacao_acao_agrupada, name='notificacao_acao_agrupada'),
    path('notificacoes/acoes-em-massa/', views.notificacoes_acoes_em_massa, name='notificacoes_acoes_em_massa'),
    
    # API (para chamadas JS)
    path('api/adicionar-entidade/', views.adicionar_entidade_simples, name='adicionar_entidade_simples'),
    path('api/adicionar-assunto/', views.adicionar_assunto, name='adicionar_assunto'),
    path('api/visualizar-questao/<int:questao_id>/', views.visualizar_questao_ajax, name='visualizar_questao_ajax'),
    
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/<int:user_id>/editar/', views.editar_usuario_staff, name='editar_usuario_staff'),
    path('usuarios/<int:user_id>/promover/', views.promover_a_superuser, name='promover_a_superuser'),
    path('usuarios/<int:user_id>/despromover/', views.despromover_de_superuser, name='despromover_de_superuser'),
    path('usuarios/<int:user_id>/deletar/', views.deletar_usuario, name='deletar_usuario'),
    
    path('usuarios/<int:user_id>/sugerir-exclusao/', views.sugerir_exclusao_usuario, name='sugerir_exclusao_usuario'),
    path('solicitacoes/exclusao/', views.listar_solicitacoes_exclusao, name='listar_solicitacoes_exclusao'),
    path('solicitacoes/exclusao/<int:solicitacao_id>/aprovar/', views.aprovar_solicitacao_exclusao, name='aprovar_solicitacao_exclusao'),
    path('solicitacoes/exclusao/<int:solicitacao_id>/rejeitar/', views.rejeitar_solicitacao_exclusao, name='rejeitar_solicitacao_exclusao'),
    path('solicitacoes/cancelar/<int:solicitacao_id>/', views.cancelar_solicitacao_exclusao, name='cancelar_solicitacao_exclusao'),
    
    path('logs/', views.listar_logs_atividade, name='listar_logs_atividade'),
    path('logs/deletar/<int:log_id>/', views.deletar_log_atividade, name='deletar_log_atividade'),
    path('logs/acoes-em-massa/', views.logs_acoes_em_massa, name='logs_acoes_em_massa'),


]