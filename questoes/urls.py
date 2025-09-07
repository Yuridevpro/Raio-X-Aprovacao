# questoes/urls.py

from django.urls import path
from . import views

app_name = 'questoes'

urlpatterns = [
    # Rota da API para buscar assuntos
    path('api/get-assuntos-por-disciplina/', views.get_assuntos_por_disciplina, name='get_assuntos_por_disciplina'),
]