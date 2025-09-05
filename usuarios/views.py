# usuarios/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import UserProfile, Ativacao, PasswordResetToken
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from questoes.models import Questao

# =======================================================================
# FUNÇÃO AUXILIAR PARA ENVIO DE E-MAILS COM TEMPLATES HTML
# =======================================================================
def enviar_email_com_template(request, subject, template_name, context, recipient_list):
    """
    Renderiza um template HTML e o envia como um e-mail.
    """
    # Adiciona o host (ex: 127.0.0.1:8000 ou raio-x-aprovacao.onrender.com) ao contexto
    # para que possamos construir links absolutos (http://...) nos templates de e-mail.
    context['host'] = request.get_host()
    
    html_content = render_to_string(template_name, context)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body='', # O corpo de texto simples é opcional, pois o HTML é o principal
        from_email=settings.EMAIL_HOST_USER, # Remetente (configurado no settings.py)
        to=recipient_list # Lista de destinatários
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


# =======================================================================
# VIEWS DE AUTENTICAÇÃO ATUALIZADAS
# =======================================================================

def cadastro(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        nome = request.POST.get('nome')
        sobrenome = request.POST.get('sobrenome')
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        confirmar_senha = request.POST.get('confirmar_senha')

        if not all([nome, sobrenome, email, senha, confirmar_senha]):
            messages.error(request, 'Todos os campos são obrigatórios!')
            return redirect('cadastro')
        if senha != confirmar_senha:
            messages.error(request, 'As senhas não coincidem!')
            return redirect('cadastro')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este e-mail já está em uso.')
            return redirect('cadastro')

        try:
            # 1. Cria o usuário, mas o mantém INATIVO até a confirmação por e-mail.
            user = User.objects.create_user(username=email, email=email, password=senha, is_active=False)
            UserProfile.objects.create(user=user, nome=nome, sobrenome=sobrenome)
            
            # 2. Cria um token de ativação para este usuário.
            ativacao = Ativacao.objects.create(user=user)
            
            # 3. Envia o e-mail de confirmação usando nossa função auxiliar.
            enviar_email_com_template(
                request,
                subject='Confirme seu Cadastro no Raio-X da Aprovação',
                template_name='usuarios/email_confirmacao.html',
                context={'user': user, 'token': ativacao.token},
                recipient_list=[user.email]
            )
            
            messages.success(request, 'Cadastro realizado! Um e-mail de confirmação foi enviado para o seu endereço. Por favor, verifique sua caixa de entrada (e spam).')
            return redirect('login')

        except Exception as e:
            messages.error(request, f'Ocorreu um erro inesperado durante o cadastro: {e}')
            return redirect('cadastro')

    return render(request, 'usuarios/cadastro.html')


def confirmar_email(request, token):
    try:
        # Tenta encontrar o token no banco de dados.
        ativacao = Ativacao.objects.get(token=token)
        
        # Verifica se o token já expirou (mais de 24 horas).
        if ativacao.is_expired():
            messages.error(request, 'Link de ativação expirado. Por favor, tente se cadastrar novamente para receber um novo link.')
            ativacao.user.delete() # Limpa o usuário inativo do banco
            return redirect('cadastro')
            
        # Ativa o usuário e deleta o token para que não possa ser usado novamente.
        user = ativacao.user
        user.is_active = True
        user.save()
        ativacao.delete()
        
        messages.success(request, 'E-mail confirmado com sucesso! Você já pode fazer o login.')
        return redirect('login')
        
    except Ativacao.DoesNotExist:
        messages.error(request, 'Link de ativação inválido ou já utilizado.')
        return redirect('cadastro')


def logar(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        email = request.POST.get('email')
        senha = request.POST.get('senha')

        if not email or not senha:
            messages.error(request, 'E-mail e senha são obrigatórios.')
            return redirect('login')
            
        try:
            # Busca o usuário pelo e-mail antes de tentar autenticar.
            user_obj = User.objects.get(email=email)
            # VERIFICA SE A CONTA ESTÁ ATIVA.
            if not user_obj.is_active:
                messages.warning(request, 'Sua conta ainda não foi ativada. Por favor, verifique o link de confirmação no seu e-mail.')
                return redirect('login')
        except User.DoesNotExist:
            # Se o usuário não existe, a mensagem de erro padrão é suficiente.
            pass

        user = authenticate(request, username=email, password=senha)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bem-vindo(a), {user.userprofile.nome}!')
            return redirect('home')
        else:
            messages.error(request, 'E-mail ou senha inválidos.')
            return redirect('login')

    return render(request, 'usuarios/login.html')

def esqueceu_senha(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            PasswordResetToken.objects.filter(user=user).delete()
            token_obj = PasswordResetToken.objects.create(user=user)
            
            enviar_email_com_template(
                request,
                subject='Redefinição de Senha - Raio-X da Aprovação',
                template_name='usuarios/email_reset_senha.html',
                context={'user': user, 'token': token_obj.token},
                recipient_list=[user.email]
            )
            
            messages.success(request, 'Um e-mail com instruções foi enviado para o seu endereço.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'Não foi encontrado um usuário com este e-mail.')
    return render(request, 'usuarios/esqueceu_senha.html')

def resetar_senha(request, token):
    try:
        token_obj = PasswordResetToken.objects.get(token=token)
        if token_obj.is_expired():
            messages.error(request, 'Link de redefinição expirado. Por favor, solicite um novo.')
            token_obj.delete()
            return redirect('esqueceu_senha')
        
        if request.method == 'POST':
            senha = request.POST.get('senha')
            confirmar_senha = request.POST.get('confirmar_senha')
            
            if senha and senha == confirmar_senha:
                user = token_obj.user
                user.set_password(senha)
                user.save()
                token_obj.delete()
                messages.success(request, 'Sua senha foi redefinida com sucesso! Faça o login.')
                return redirect('login')
            else:
                messages.error(request, 'As senhas não coincidem.')
        
        return render(request, 'usuarios/resetar_senha.html')

    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Link de redefinição inválido.')
        return redirect('esqueceu_senha')

@login_required
def sair(request):
    logout(request)
    messages.info(request, 'Você saiu da sua conta.')
    return redirect('login')

def home(request):
    total_questoes = Questao.objects.count()
    context = {'total_questoes': total_questoes}
    return render(request, 'home.html', context)

@login_required
def editar_perfil(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        nome = request.POST.get('nome')
        sobrenome = request.POST.get('sobrenome')
        if not nome or not sobrenome:
            messages.error(request, 'Nome e sobrenome são obrigatórios.')
        else:
            user_profile.nome = nome
            user_profile.sobrenome = sobrenome
            user_profile.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('home')
    return render(request, 'usuarios/editar_perfil.html', {'user_profile': user_profile})

@login_required
def alterar_senha(request):
    if request.method == 'POST':
        senha_atual = request.POST.get('senha_atual')
        nova_senha = request.POST.get('nova_senha')
        confirmar_senha = request.POST.get('confirmar_senha')
        user = request.user
        if not user.check_password(senha_atual):
            messages.error(request, 'A senha atual está incorreta.')
            return redirect('alterar_senha')
        if nova_senha != confirmar_senha:
            messages.error(request, 'As novas senhas não coincidem.')
            return redirect('alterar_senha')
        user.set_password(nova_senha)
        user.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Senha alterada com sucesso!')
        return redirect('alterar_senha')
    return render(request, 'usuarios/alterar_senha.html')

# --- INÍCIO DA NOVA VIEW ---
@login_required
def deletar_conta(request):
    if request.method == 'POST':
        user = request.user
        # O Django deleta em cascata: ao deletar o User, o UserProfile também será deletado.
        user.delete()
        logout(request)
        messages.success(request, 'Sua conta foi excluída com sucesso.')
        return redirect('home') # Redireciona para a página inicial após a exclusão
    
    # Se a requisição não for POST, redireciona para a página de edição de perfil.
    return redirect('editar_perfil')
# --- FIM DA NOVA VIEW ---