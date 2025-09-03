# usuarios/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.logar, name='login'),
    path('sair/', views.sair, name='sair'),
    path('esqueceu-senha/', views.esqueceu_senha, name='esqueceu_senha'),
    path('resetar-senha/<uuid:token>/', views.resetar_senha, name='resetar_senha'),
     # ADICIONE ESTAS DUAS LINHAS
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/alterar-senha/', views.alterar_senha, name='alterar_senha')
]