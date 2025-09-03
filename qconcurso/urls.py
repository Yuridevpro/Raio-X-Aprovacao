# qconcurso/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Importando a view home temporária
from usuarios.views import home

# qconcurso/urls.py


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('usuarios.urls')),
    path('pratica/', include('pratica.urls')), 
    path('desempenho/', include('desempenho.urls')),
    path('', home, name='home'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)