# usuarios/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import UserProfile
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from .models import PasswordResetToken
from questoes.models import Questao

def cadastro(request):
    # --- ADICIONADO ---
    # Se o usuário já está logado, impede o acesso à página de cadastro.
    if request.user.is_authenticated:
        return redirect('home')
    # --- FIM DA ADIÇÃO ---

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
            user = User.objects.create_user(username=email, email=email, password=senha)
            UserProfile.objects.create(user=user, nome=nome, sobrenome=sobrenome)
            messages.success(request, 'Cadastro realizado com sucesso! Faça o login.')
            return redirect('login')

        except Exception as e:
            messages.error(request, f'Ocorreu um erro: {e}')
            return redirect('cadastro')

    return render(request, 'usuarios/cadastro.html')


def logar(request):
    # --- ADICIONADO ---
    # Se o usuário já está logado, impede o acesso à página de login.
    if request.user.is_authenticated:
        return redirect('home')
    # --- FIM DA ADIÇÃO ---

    if request.method == "POST":
        email = request.POST.get('email')
        senha = request.POST.get('senha')

        if not email or not senha:
            messages.error(request, 'E-mail e senha são obrigatórios.')
            return redirect('login')

        user = authenticate(request, username=email, password=senha)

        if user is not None:
            login(request, user)
            messages.success(request, f'Bem-vindo(a), {user.userprofile.nome}!')
            return redirect('home')
        else:
            messages.error(request, 'E-mail ou senha inválidos.')
            return redirect('login')

    return render(request, 'usuarios/login.html')

@login_required
def sair(request):
    logout(request)
    messages.info(request, 'Você saiu da sua conta.')
    return redirect('login')

def home(request):
    total_questoes = Questao.objects.count()
    context = {
        'total_questoes': total_questoes
    }
    return render(request, 'home.html', context)

def enviar_email_reset(request, user, token_obj):
    reset_link = request.build_absolute_uri(
        reverse('resetar_senha', kwargs={'token': token_obj.token})
    )
    subject = 'Redefinição de Senha - QConcurso'
    message = (
        f'Olá {user.userprofile.nome},\n\n'
        f'Você solicitou a redefinição da sua senha. Clique no link abaixo para criar uma nova senha:\n'
        f'{reset_link}\n\n'
        f'Se você não solicitou isso, por favor, ignore este e-mail.\n\n'
        f'Atenciosamente,\nEquipe QConcurso'
    )
    # A linha abaixo vai imprimir o email no console (por causa do EMAIL_BACKEND console)
    # Em produção, com o backend SMTP, ela enviará o email de verdade.
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])

def esqueceu_senha(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            PasswordResetToken.objects.filter(user=user).delete()
            token_obj = PasswordResetToken.objects.create(user=user)
            enviar_email_reset(request, user, token_obj)
            messages.success(request, 'Um e-mail com instruções para redefinir sua senha foi enviado.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'Não foi encontrado um usuário com este endereço de e-mail.')
    return render(request, 'usuarios/esqueceu_senha.html')

def resetar_senha(request, token):
    try:
        token_obj = PasswordResetToken.objects.get(token=token)
        if token_obj.is_expired():
            messages.error(request, 'Este link de redefinição de senha expirou.')
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
                messages.success(request, 'Sua senha foi redefinida com sucesso! Você já pode fazer o login.')
                return redirect('login')
            else:
                messages.error(request, 'As senhas não coincidem.')
        
        return render(request, 'usuarios/resetar_senha.html', {'token': token})

    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Link de redefinição de senha inválido.')
        return redirect('esqueceu_senha')

# usuarios/views.py

@login_required
def editar_perfil(request):
    # --- LINHA ALTERADA ---
    # get_or_create: busca o perfil. Se não existir, cria um vazio e o retorna.
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
            # Após salvar com sucesso, redireciona para a home ou dashboard
            return redirect('home')
            
    return render(request, 'usuarios/editar_perfil.html')

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