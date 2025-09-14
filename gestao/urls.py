# gestao/urls.py

from django.urls import path
from . import views

app_name = 'gestao'

urlpatterns = [
    # DASHBOARD
    path('', views.dashboard_gestao, name='dashboard'),

    # GERENCIAMENTO DE QUESTÕES
    path('questoes/', views.listar_questoes_gestao, name='listar_questoes'),
    path('questoes/nova/', views.adicionar_questao, name='adicionar_questao'),
    path('questoes/editar/<int:questao_id>/', views.editar_questao, name='editar_questao'),
    path('questoes/deletar/<int:questao_id>/', views.deletar_questao, name='deletar_questao'),
    path('questoes/acoes-em-massa/', views.questoes_acoes_em_massa, name='questoes_acoes_em_massa'),
    
    # URLs da Lixeira de Questões
    path('questoes/lixeira/', views.listar_questoes_deletadas, name='listar_questoes_deletadas'),
    path('questoes/lixeira/acoes-em-massa/', views.questoes_deletadas_acoes_em_massa, name='questoes_deletadas_acoes_em_massa'),
    path('questoes/<int:questao_id>/restaurar/', views.restaurar_questao, name='restaurar_questao'),
    path('questoes/<int:questao_id>/deletar-permanente/', views.deletar_questao_permanente, name='deletar_questao_permanente'),
    
    
    # GERENCIAMENTO DE USUÁRIOS
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/<int:user_id>/editar/', views.editar_usuario_staff, name='editar_usuario_staff'),
    path('usuarios/<int:user_id>/deletar/', views.deletar_usuario, name='deletar_usuario'),

    # --- Sistema de Promoção com Quorum ---
    path('usuarios/promocao/solicitar/<int:user_id>/', views.solicitar_promocao_superuser, name='solicitar_promocao_superuser'),
    path('usuarios/promocao/solicitacoes/', views.listar_solicitacoes_promocao, name='listar_solicitacoes_promocao'),
    path('usuarios/promocao/aprovar/<int:promocao_id>/', views.aprovar_promocao_superuser, name='aprovar_promocao_superuser'),
    path('usuarios/promocao/cancelar/<int:promocao_id>/', views.cancelar_promocao_superuser, name='cancelar_promocao_superuser'),
    path('usuarios/promocao/direta/<int:user_id>/', views.promover_diretamente_superuser, name='promover_diretamente_superuser'),
    
    
    # --- Sistema de Despromoção com Quorum ---
    path('usuarios/despromocao/solicitar/<int:user_id>/', views.solicitar_despromocao_superuser, name='solicitar_despromocao_superuser'),
    path('usuarios/despromocao/solicitacoes/', views.listar_solicitacoes_despromocao, name='listar_solicitacoes_despromocao'),
    path('usuarios/despromocao/aprovar/<int:despromocao_id>/', views.aprovar_despromocao_superuser, name='aprovar_despromocao_superuser'),
    path('usuarios/despromocao/cancelar/<int:despromocao_id>/', views.cancelar_despromocao_superuser, name='cancelar_despromocao_superuser'),
    
    # --- Sistema de exclusao com Quorum ---
    path('usuarios/exclusao-superuser/solicitar/<int:user_id>/', views.solicitar_exclusao_superuser, name='solicitar_exclusao_superuser'),
    path('usuarios/exclusao-superuser/solicitacoes/', views.listar_solicitacoes_exclusao_superuser, name='listar_solicitacoes_exclusao_superuser'),
    path('usuarios/exclusao-superuser/aprovar/<int:exclusao_id>/', views.aprovar_exclusao_superuser, name='aprovar_exclusao_superuser'),
    path('usuarios/exclusao-superuser/cancelar/<int:exclusao_id>/', views.cancelar_exclusao_superuser, name='cancelar_exclusao_superuser'),

    # --- Sistema de Exclusão com Solicitação ---
    path('usuarios/<int:user_id>/sugerir-exclusao/', views.sugerir_exclusao_usuario, name='sugerir_exclusao_usuario'),
    path('solicitacoes/exclusao/', views.listar_solicitacoes_exclusao, name='listar_solicitacoes_exclusao'),
    path('solicitacoes/exclusao/<int:solicitacao_id>/aprovar/', views.aprovar_solicitacao_exclusao, name='aprovar_solicitacao_exclusao'),
    path('solicitacoes/exclusao/<int:solicitacao_id>/rejeitar/', views.rejeitar_solicitacao_exclusao, name='rejeitar_solicitacao_exclusao'),
    path('solicitacoes/cancelar/<int:solicitacao_id>/', views.cancelar_solicitacao_exclusao, name='cancelar_solicitacao_exclusao'),
    
    # GERENCIAMENTO DE NOTIFICAÇÕES DE ERRO
    path('notificacoes/', views.listar_notificacoes, name='listar_notificacoes'),
    path('notificacoes/acao/<int:content_type_id>/<int:object_id>/', views.notificacao_acao_agrupada, name='notificacao_acao_agrupada'),
    path('notificacoes/acoes-em-massa/', views.notificacoes_acoes_em_massa, name='notificacoes_acoes_em_massa'),

    # LOGS DE ATIVIDADE E AUDITORIA
    path('logs/', views.listar_logs_atividade, name='listar_logs_atividade'),
    path('logs/deletar/<int:log_id>/', views.deletar_log_atividade, name='deletar_log_atividade'),
    path('logs/acoes-em-massa/', views.logs_acoes_em_massa, name='logs_acoes_em_massa'),
    path('logs/mover-para-lixeira/', views.mover_logs_antigos_para_lixeira, name='mover_logs_antigos_para_lixeira'),
    path('logs/lixeira/', views.listar_logs_deletados, name='listar_logs_deletados'),
    
    # API ENDPOINTS (para chamadas via JavaScript)
    path('api/adicionar-entidade/', views.adicionar_entidade_simples, name='adicionar_entidade_simples'),
    path('api/adicionar-assunto/', views.adicionar_assunto, name='adicionar_assunto'),
    path('api/visualizar-questao/<int:questao_id>/', views.visualizar_questao_ajax, name='visualizar_questao_ajax'),
    path('api/visualizar-comentario/<int:comentario_id>/', views.visualizar_comentario_ajax, name='visualizar_comentario_ajax'),
    
    # =======================================================================
    # INÍCIO DA CORREÇÃO: Sintaxe dos conversores de caminho
    # =======================================================================
    path('simulados/', views.listar_simulados_gestao, name='listar_simulados_gestao'),
    path('simulados/novo/', views.criar_simulado, name='criar_simulado'),
    path('simulados/editar/<int:simulado_id>/', views.editar_simulado, name='editar_simulado'),
    path('simulados/deletar/<int:simulado_id>/', views.deletar_simulado, name='deletar_simulado'),
    path('simulados/api/gerenciar-questoes/<int:simulado_id>/', views.gerenciar_questoes_simulado_ajax, name='gerenciar_questoes_simulado_ajax'),
    path('simulados/api/contar-questoes/', views.api_contar_questoes_filtro, name='api_contar_questoes_filtro'),
    path('simulados/api/editar-meta/<int:simulado_id>/', views.editar_simulado_meta_ajax, name='editar_simulado_meta_ajax'),

    
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================
]