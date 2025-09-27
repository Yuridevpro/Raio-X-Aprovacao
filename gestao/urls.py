# gestao/urls.py (ARQUIVO COMPLETO E FINALIZADO)

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
    path('logs/lixeira/limpar/', views.limpar_lixeira_logs, name='limpar_lixeira_logs'),

    path('logs/lixeira/', views.listar_logs_deletados, name='listar_logs_deletados'),
    path('logs/lixeira/solicitar-exclusao/', views.solicitar_exclusao_logs, name='solicitar_exclusao_logs'),
    path('logs/solicitacoes-exclusao/', views.listar_solicitacoes_exclusao_logs, name='listar_solicitacoes_exclusao_logs'),
    path('logs/solicitacoes-exclusao/aprovar/<int:solicitacao_id>/', views.aprovar_exclusao_logs, name='aprovar_exclusao_logs'),
    
    # API ENDPOINTS (para chamadas via JavaScript)
    path('api/adicionar-entidade/', views.adicionar_entidade_simples, name='adicionar_entidade_simples'),
    path('api/adicionar-assunto/', views.adicionar_assunto, name='adicionar_assunto'),
    path('api/visualizar-questao/<int:questao_id>/', views.visualizar_questao_ajax, name='visualizar_questao_ajax'),
    path('api/visualizar-comentario/<int:comentario_id>/', views.visualizar_comentario_ajax, name='visualizar_comentario_ajax'),
    
    path('simulados/', views.listar_simulados_gestao, name='listar_simulados_gestao'),
    path('simulados/novo/', views.criar_simulado, name='criar_simulado'),
    path('simulados/editar/<int:simulado_id>/', views.editar_simulado, name='editar_simulado'),
    path('simulados/deletar/<int:simulado_id>/', views.deletar_simulado, name='deletar_simulado'),
    path('simulados/api/gerenciar-questoes/<int:simulado_id>/', views.gerenciar_questoes_simulado_ajax, name='gerenciar_questoes_simulado_ajax'),
    path('simulados/api/contar-questoes/', views.api_contar_questoes_filtro, name='api_contar_questoes_filtro'),
    path('simulados/api/editar-meta/<int:simulado_id>/', views.editar_simulado_meta_ajax, name='editar_simulado_meta_ajax'),
    
    # =======================================================================
    # URLS DE GAMIFICAÇÃO (FLUXO ATUALIZADO)
    # =======================================================================
    path('gamificacao/dashboard/', views.dashboard_gamificacao, name='dashboard_gamificacao'),
    path('gamificacao/conceder-recompensa/', views.conceder_recompensa_manual, name='conceder_recompensa_manual'),
    path('gamificacao/configuracoes/', views.gerenciar_gamificacao_settings, name='gerenciar_gamificacao_settings'),
    path('gamificacao/campanhas/', views.listar_campanhas, name='listar_campanhas'),
    path('gamificacao/campanhas/nova/', views.criar_ou_editar_campanha, name='criar_campanha'),
    path('gamificacao/campanhas/editar/<int:campanha_id>/', views.criar_ou_editar_campanha, name='editar_campanha'),
    path('gamificacao/campanhas/deletar/<int:campanha_id>/', views.deletar_campanha, name='deletar_campanha'),

    # --- URLs de Trilhas ---
    path('gamificacao/trilhas/', views.listar_trilhas, name='listar_trilhas'),
    path('gamificacao/trilhas/nova/', views.criar_ou_editar_trilha, name='criar_trilha'),
    path('gamificacao/trilhas/editar/<int:trilha_id>/', views.criar_ou_editar_trilha, name='editar_trilha'),
    path('gamificacao/trilhas/deletar/<int:trilha_id>/', views.deletar_trilha, name='deletar_trilha'),
    
    # --- URLs de Séries de Conquistas (NOVO FLUXO) ---
    path('gamificacao/trilhas/<int:trilha_id>/series/nova/', views.criar_serie, name='criar_serie'),
    path('gamificacao/series/<int:serie_id>/gerenciar/', views.gerenciar_serie, name='gerenciar_serie'),
    path('gamificacao/series/<int:serie_id>/reordenar/', views.reordenar_conquistas_ajax, name='reordenar_conquistas_ajax'),
    path('gamificacao/series/<int:serie_id>/deletar/', views.deletar_serie, name='deletar_serie'),

    # --- URLs de Conquistas (FLUXO ATUALIZADO E CONTEXTUAL) ---
    path('gamificacao/trilhas/<int:trilha_id>/conquistas/', views.gerenciar_conquistas_da_trilha, name='gerenciar_conquistas_da_trilha'),
    # Criar conquista individual
    path('gamificacao/trilhas/<int:trilha_id>/conquistas/nova/', views.criar_ou_editar_conquista, name='criar_conquista_individual'),
    # Criar primeira conquista de uma série
    path('gamificacao/series/<int:serie_id>/conquistas/nova/', views.criar_ou_editar_conquista, name='criar_primeira_conquista_serie'),
    # Criar conquista sequencial
    path('gamificacao/series/<int:serie_id>/conquistas/nova/apos/<int:previous_conquista_id>/', views.criar_ou_editar_conquista, name='criar_conquista_sequencial'),
    # Editar conquista (URL única)
    path('gamificacao/conquistas/editar/<int:conquista_id>/', views.criar_ou_editar_conquista, name='editar_conquista'),
    path('gamificacao/conquistas/deletar/<int:conquista_id>/', views.deletar_conquista, name='deletar_conquista'),
    
    # --- URLs de Variáveis do Jogo ---
    path('gamificacao/variaveis/', views.listar_variaveis_do_jogo, name='listar_variaveis_do_jogo'),
    path('gamificacao/variaveis/nova/', views.criar_ou_editar_variavel, name='criar_variavel_do_jogo'),
    path('gamificacao/variaveis/editar/<int:variavel_id>/', views.criar_ou_editar_variavel, name='editar_variavel_do_jogo'),
    
    # --- Rotas de Recompensas Genéricas ---
    path('gamificacao/<str:tipo>/', views.listar_recompensas, name='listar_recompensas'),
    path('gamificacao/<str:tipo>/nova/', views.criar_recompensa, name='criar_recompensa'),
    path('gamificacao/<str:tipo>/editar/<int:recompensa_id>/', views.editar_recompensa, name='editar_recompensa'),
    path('gamificacao/<str:tipo>/deletar/<int:recompensa_id>/', views.deletar_recompensa, name='deletar_recompensa'),
]