# gamificacao/urls.py (NOVO ARQUIVO)

from django.urls import path
from . import views

app_name = 'gamificacao'

urlpatterns = [
    # URL principal da página de Ranking
    path('ranking/', views.ranking, name='ranking'),
    path('loja/', views.loja, name='loja'),
    path('api/comprar-item/', views.comprar_item_ajax, name='comprar_item'),
    path('api/resgatar-recompensa/', views.resgatar_recompensa_ajax, name='resgatar_recompensa'),
    path('eventos/', views.campanhas_ativas, name='campanhas_ativas'),

]