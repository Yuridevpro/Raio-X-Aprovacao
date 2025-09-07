# usuarios/middleware.py

from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.conf import settings
from django.contrib.auth import logout
from django.contrib import messages
from .models import UserProfile

class ProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return self.get_response(request)
            
            allowed_urls = [
                reverse('editar_perfil'),
                reverse('sair'),
                reverse('alterar_senha'),
            ]
            
            # Usamos hasattr para uma verificação segura, sem causar erros.
            if not hasattr(request.user, 'userprofile'):
                if request.path not in allowed_urls:
                    messages.warning(request, 'Por favor, complete seu perfil para continuar.')
                    return redirect('editar_perfil')
        
        return self.get_response(request)