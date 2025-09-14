# gamificacao/urls.py (NOVO ARQUIVO)

from django.urls import path
from . import views

app_name = 'gamificacao'

urlpatterns = [
    # URL principal da página de Ranking
    path('ranking/', views.ranking, name='ranking'),
]