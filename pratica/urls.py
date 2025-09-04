# pratica/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # URL para a página de filtros e lista de questões
    path('', views.listar_questoes, name='listar_questoes'),
    # URL que o nosso AJAX vai chamar para verificar uma resposta
    path('verificar-resposta/', views.verificar_resposta, name='verificar_resposta'),
    path('favoritar-questao/', views.favoritar_questao, name='favoritar_questao'),
  
    path('adicionar-comentario/', views.adicionar_comentario, name='adicionar_comentario'),
    path('carregar-comentarios/<int:questao_id>/', views.carregar_comentarios, name='carregar_comentarios'),
    
    path('api/get-assuntos-por-disciplina/', views.get_assuntos_por_disciplina, name='get_assuntos_por_disciplina'),
    
        # --- INÍCIO DAS NOVAS URLS ---
    path('editar-comentario/', views.editar_comentario, name='editar_comentario'),
    path('excluir-comentario/', views.excluir_comentario, name='excluir_comentario'),
    
    path('api/salvar-filtro/', views.salvar_filtro, name='salvar_filtro'),
    path('api/deletar-filtro/', views.deletar_filtro, name='deletar_filtro'),
    
    path('toggle-like-comentario/', views.toggle_like_comentario, name='toggle_like_comentario'),

]