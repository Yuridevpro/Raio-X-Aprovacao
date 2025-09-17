# simulados/urls.py

from django.urls import path
from . import views

app_name = 'simulados'

urlpatterns = [
    path('', views.listar_simulados, name='listar_simulados'),
    path('oficiais/', views.listar_simulados_oficiais, name='listar_simulados_oficiais'),
    
    # ROTA PRINCIPAL DE GERAÇÃO AGORA APONTA PARA A VIEW AVANÇADA
    path('gerar/', views.gerar_simulado_avancado, name='gerar_simulado_usuario'),
    
    # NOVA ROTA DE API
    path('api/contar-questoes-disciplina/', views.api_contar_questoes_por_disciplina, name='api_contar_questoes_por_disciplina'),
    
    # ROTAS EXISTENTES
    path('<int:simulado_id>/iniciar/', views.iniciar_ou_continuar_sessao, name='iniciar_ou_continuar_sessao'),
    path('<int:simulado_id>/excluir/', views.excluir_simulado, name='excluir_simulado'),
    path('sessao/<int:sessao_id>/realizar/', views.realizar_simulado, name='realizar_simulado'),
    path('sessao/<int:sessao_id>/registrar_resposta/', views.registrar_resposta_simulado, name='registrar_resposta_simulado'),
    path('sessao/<int:sessao_id>/finalizar/', views.finalizar_simulado, name='finalizar_simulado'),
    path('sessao/<int:sessao_id>/resultado/', views.resultado_simulado, name='resultado_simulado'),
    
    
    path('<int:simulado_id>/historico/', views.historico_simulado, name='historico_simulado'),
    path('sessao/<int:sessao_id>/excluir/', views.excluir_sessao_simulado, name='excluir_sessao_simulado'),
    path('<int:simulado_id>/limpar-historico/', views.limpar_historico_simulado, name='limpar_historico_simulado'),
]