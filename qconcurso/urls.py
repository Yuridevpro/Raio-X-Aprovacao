# qconcurso/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Importando a view home temporária
from usuarios.views import home
from usuarios.views import home


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('usuarios.urls')),
    path('pratica/', include('pratica.urls')), 
    path('desempenho/', include('desempenho.urls')),
    path('gestao/', include('gestao.urls', namespace='gestao')),
    path('questoes/', include('questoes.urls', namespace='questoes')),
    path('simulados/', include('simulados.urls', namespace='simulados')),
    path('', home, name='home'),
    path('', include('gamificacao.urls', namespace='gamificacao')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)