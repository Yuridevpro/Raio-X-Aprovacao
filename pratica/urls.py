# pratica/urls.py

from django.urls import path
from . import views

# =======================================================================
# Adicionando o app_name para garantir que as URLs como {% url 'pratica:listar_questoes' %} funcionem
# =======================================================================
app_name = 'pratica'

urlpatterns = [
    # URL para a página de filtros e lista de questões
    path('', views.listar_questoes, name='listar_questoes'),
    
    # URLs de API para interações com as questões
    path('verificar-resposta/', views.verificar_resposta, name='verificar_resposta'),
    path('favoritar-questao/', views.favoritar_questao, name='favoritar_questao'),
    path('api/notificar-erro/', views.notificar_erro, name='notificar_erro'),

    
    # URLs de API para comentários
    path('adicionar-comentario/', views.adicionar_comentario, name='adicionar_comentario'),
    path('carregar-comentarios/<int:questao_id>/', views.carregar_comentarios, name='carregar_comentarios'),
    path('editar-comentario/', views.editar_comentario, name='editar_comentario'),
    path('excluir-comentario/', views.excluir_comentario, name='excluir_comentario'),
    path('toggle-like-comentario/', views.toggle_like_comentario, name='toggle_like_comentario'),
    
    # URLs de API para filtros salvos
    path('api/salvar-filtro/', views.salvar_filtro, name='salvar_filtro'),
    path('api/deletar-filtro/', views.deletar_filtro, name='deletar_filtro'),
    
    # =======================================================================
    # A URL abaixo foi REMOVIDA, pois a view foi centralizada no app 'questoes'.
    # A nova URL a ser usada nos templates é {% url 'questoes:get_assuntos_por_disciplina' %}
    # path('api/get-assuntos-por-disciplina/', views.get_assuntos_por_disciplina, name='get_assuntos_por_disciplina'),
    # =======================================================================
]