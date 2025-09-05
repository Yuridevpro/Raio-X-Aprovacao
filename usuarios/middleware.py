# usuarios/middleware.py

from django.shortcuts import redirect
from django.urls import reverse, resolve
from usuarios.models import UserProfile # Importe seu modelo UserProfile

class ProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Primeiro, executa a requisição para obter a resposta
        response = self.get_response(request)

        # O middleware só age se o usuário estiver autenticado
        if request.user.is_authenticated:
            
            # IGNORA superusuários (admins) para que eles possam acessar o /admin/
            if request.user.is_superuser:
                return response
            
            # Define as URLs que o usuário PODE acessar sem ter um perfil completo
            allowed_urls = [
                reverse('editar_perfil'),
                reverse('sair'),
                # Adicione aqui outras URLs se necessário, como 'alterar_senha'
            ]
            
            # Verifica se o usuário tem um perfil.
            # hasattr() é uma forma segura de checar a existência do perfil sem causar um erro.
            if not hasattr(request.user, 'userprofile'):
                # Se não tem perfil E não está tentando acessar uma das URLs permitidas...
                if request.path not in allowed_urls:
                    # ...redireciona para a página de edição de perfil.
                    return redirect('editar_perfil')
        
        return response

# --- INÍCIO DO NOVO MIDDLEWARE DE SESSÃO DO ADMIN ---
class AdminSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verifica se a URL da requisição pertence ao namespace 'admin'
        # Esta é a forma mais robusta de identificar uma URL do admin
        if resolve(request.path_info).app_name == 'admin':
            # Se for uma URL do admin, troca o nome do cookie de sessão
            # que o Django usará para esta requisição específica.
            request.session.model._meta.db_table = 'django_admin_sessions'
            settings.SESSION_COOKIE_NAME = settings.ADMIN_SESSION_COOKIE_NAME
        else:
            # Para todas as outras URLs, garante que o cookie padrão seja usado
            settings.SESSION_COOKIE_NAME = 'qconcurso_sessionid'
            
        response = self.get_response(request)
        
        return response
# --- FIM DO NOVO MIDDLEWARE ---