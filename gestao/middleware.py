# gestao/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
import os

class SuperuserAdminAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_user = os.getenv('SUPERUSER_ADMIN_USERNAME')
        self.admin_pass = os.getenv('SUPERUSER_ADMIN_PASSWORD')

    def __call__(self, request):
        if request.path.startswith(reverse('admin:index')):
            
            if not self.admin_user or not self.admin_pass:
                return redirect('home')

            if request.session.get('superuser_admin_authenticated', False):
                return self.get_response(request)

            # =======================================================================
            # CORREÇÃO APLICADA AQUI
            # Adicionado o namespace 'gestao:' antes do nome da rota.
            # =======================================================================
            login_url = reverse('gestao:superuser_admin_login')
            # =======================================================================
            # FIM DA CORREÇÃO
            # =======================================================================
            
            return redirect(f'{login_url}?next={request.path}')
            
        return self.get_response(request)