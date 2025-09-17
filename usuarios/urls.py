# usuarios/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.logar, name='login'),
    path('sair/', views.sair, name='sair'),
    
    path('confirmar-email/<uuid:token>/', views.confirmar_email, name='confirmar_email'),
    path('esqueceu-senha/', views.esqueceu_senha, name='esqueceu_senha'),
    path('resetar-senha/<uuid:token>/', views.resetar_senha, name='resetar_senha'),
    path('reenviar-ativacao/', views.reenviar_ativacao, name='reenviar_ativacao'),
    
    # =======================================================================
    # ORDEM CORRIGIDA DAS URLS DE PERFIL
    # =======================================================================
    # 1. URL para o perfil do próprio usuário (sem parâmetros)
    path('perfil/', views.meu_perfil, name='meu_perfil'),
    
    # 2. URLs específicas que começam com 'perfil/'
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/alterar-senha/', views.alterar_senha, name='alterar_senha'),
    path('perfil/deletar-conta/', views.deletar_conta, name='deletar_conta'),
    path('perfil/colecao/', views.colecao, name='colecao'),
    path('perfil/equipar-avatar/<int:avatar_id>/', views.equipar_avatar, name='equipar_avatar'),
    path('perfil/equipar-borda/<int:borda_id>/', views.equipar_borda, name='equipar_borda'),

    # 3. URL genérica com <str:username> (deve ser a ÚLTIMA)
    path('perfil/<str:username>/', views.visualizar_perfil, name='visualizar_perfil'),
]