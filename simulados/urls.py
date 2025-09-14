# simulados/urls.py

from django.urls import path
from . import views

app_name = 'simulados'

urlpatterns = [
    # Rota principal para listar todos os simulados disponíveis.
    path('', views.listar_simulados, name='listar_simulados'),

    # Rota para a página de geração de simulados personalizados.
    path('gerar/', views.gerar_simulado_usuario, name='gerar_simulado_usuario'),
    
    # =================================================================
    # ADIÇÃO: Rota para iniciar ou continuar uma sessão de simulado.
    # Esta era uma das rotas que estava faltando.
    # =================================================================
    path('<int:simulado_id>/iniciar/', views.iniciar_ou_continuar_sessao, name='iniciar_ou_continuar_sessao'),

    # =================================================================
    # ADIÇÃO: Rota para a exclusão de um simulado.
    # Essencial para a funcionalidade de exclusão que implementamos.
    # =================================================================
    path('<int:simulado_id>/excluir/', views.excluir_simulado, name='excluir_simulado'),

    # --- Rotas Relacionadas a uma Sessão Específica de Simulado ---

    # Rota para a página de realização do simulado (onde o usuário responde as questões).
    # CORREÇÃO: O caminho foi padronizado para maior clareza.
    path('sessao/<int:sessao_id>/realizar/', views.realizar_simulado, name='realizar_simulado'),

    # Endpoint (API) para registrar a resposta de uma questão (usado por JavaScript/AJAX).
    # CORREÇÃO: O nome da URL foi ajustado para corresponder à view.
    path('sessao/<int:sessao_id>/registrar_resposta/', views.registrar_resposta_simulado, name='registrar_resposta_simulado'),

    # Rota para finalizar a sessão do simulado e calcular os resultados.
    path('sessao/<int:sessao_id>/finalizar/', views.finalizar_simulado, name='finalizar_simulado'),

    # Rota para exibir a página de resultados do simulado.
    # CORREÇÃO: Removida a duplicata e padronizado o caminho.
    path('sessao/<int:sessao_id>/resultado/', views.resultado_simulado, name='resultado_simulado'),
]