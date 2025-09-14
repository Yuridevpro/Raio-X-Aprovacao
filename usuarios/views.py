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
from gestao.views import criar_log
from gestao.models import LogAtividade
from .utils import enviar_email_com_template
from django.db import transaction  # 1. IMPORTAR transaction
from gamificacao.models import ProfileStreak, ConquistaUsuario


# =======================================================================
# VIEWS DE AUTENTICAÇÃO ATUALIZADAS
# =======================================================================

@transaction.atomic  # 2. APLICAR O DECORADOR DE TRANSAÇÃO
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

        # =======================================================================
        # 3. LÓGICA INTELIGENTE PARA E-MAILS JÁ EXISTENTES
        # =======================================================================
        try:
            user_existente = User.objects.get(email=email)
            # Se o usuário existe, mas está inativo, provavelmente falhou no envio de e-mail anterior.
            if not user_existente.is_active:
                # Remove o usuário antigo para permitir uma nova tentativa de cadastro.
                user_existente.delete() 
            else:
                # Se o usuário existe E está ativo, o e-mail está realmente em uso.
                messages.error(request, 'Este e-mail já está em uso por uma conta ativa.')
                return redirect('cadastro')
        except User.DoesNotExist:
            # O e-mail não existe, podemos prosseguir normalmente.
            pass
        # =======================================================================
        # FIM DA LÓGICA INTELIGENTE
        # =======================================================================

        try:
            # Todo o bloco de criação e envio de e-mail agora está dentro de uma transação.
            # Se 'enviar_email_com_template' falhar, o 'User.objects.create_user' será desfeito.
            
            user = User.objects.create_user(username=email, email=email, password=senha, is_active=False)
            UserProfile.objects.create(user=user, nome=nome, sobrenome=sobrenome)
            
            ativacao = Ativacao.objects.create(user=user)
            
            enviar_email_com_template(
                request,
                subject='Confirme seu Cadastro no Raio-X da Aprovação',
                template_name='usuarios/email_confirmacao.html',
                context={'user': user, 'token': ativacao.token},
                recipient_list=[user.email]
            )
            
            messages.success(request, 'Cadastro realizado! Um e-mail de confirmação foi enviado. Por favor, verifique sua caixa de entrada (e spam).')
            return redirect('login')

        except Exception as e:
            # Graças ao @transaction.atomic, qualquer usuário criado aqui será revertido.
            messages.error(request, f'Ocorreu um erro inesperado durante o cadastro. Nenhuma conta foi criada. Por favor, tente novamente.')
            # Logar o erro real para depuração do administrador seria uma boa prática aqui.
            print(f"Erro de cadastro: {e}") 
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
def meu_perfil(request):
    """
    Exibe a página de perfil do usuário logado, com suas estatísticas
    de gamificação (streaks e conquistas).
    """
    user_profile = request.user.userprofile
    
    # Busca os dados de streak do usuário. get_or_create garante que ele exista.
    streak_data, _ = ProfileStreak.objects.get_or_create(user_profile=user_profile)
    
    # Busca as conquistas desbloqueadas pelo usuário, otimizando com select_related
    conquistas_usuario = ConquistaUsuario.objects.filter(
        user_profile=user_profile
    ).select_related('conquista').order_by('-data_conquista')

    context = {
        'user_profile': user_profile,
        'streak_data': streak_data,
        'conquistas_usuario': conquistas_usuario,
    }
    
    return render(request, 'usuarios/meu_perfil.html', context)
# =======================================================================
# FIM DA ADIÇÃO
# =======================================================================


@login_required
def editar_perfil(request):
    """
    Página dedicada para o usuário editar suas informações pessoais.
    A lógica de gamificação foi movida para a view `meu_perfil`.
    """
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
            # Redireciona para a nova página de perfil após salvar
            return redirect('meu_perfil') 
            
    # O contexto agora é mais simples, apenas com os dados do formulário.
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

@login_required
def deletar_conta(request):
    if request.method == 'POST':
        user = request.user

        # Verificação de segurança para o último superusuário (já implementada)
        if user.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
            messages.error(request, 'Ação negada: Você não pode excluir sua própria conta porque você é o único superusuário restante no sistema.')
            messages.info(request, 'Para realizar esta ação, primeiro promova outro usuário a superusuário através do painel de gestão.')
            return redirect('editar_perfil')

        # =======================================================================
        # INÍCIO DA ADIÇÃO: Criação do log antes da exclusão
        # =======================================================================
        # Captura o nome de usuário antes que o objeto seja deletado
        username = user.username

        # Cria o log de atividade ANTES de deletar o usuário
        criar_log(
            ator=user, # O usuário ainda existe neste ponto
            acao=LogAtividade.Acao.USUARIO_DELETADO,
            alvo=None, # Não há um objeto alvo específico além do próprio usuário
            detalhes={
                'usuario_deletado': username,
                'motivo': 'Usuário excluiu a própria conta através da página de perfil.'
            }
        )
        # =======================================================================
        # FIM DA ADIÇÃO
        # =======================================================================
        
        # O processo de exclusão continua normalmente
        user.delete()
        logout(request)
        messages.success(request, 'Sua conta foi excluída com sucesso.')
        return redirect('home')
    
    return redirect('editar_perfil')


def reenviar_ativacao(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                messages.info(request, 'Esta conta já está ativa. Você pode fazer o login.')
                return redirect('login')
            
            # Deleta qualquer token de ativação antigo para garantir que apenas o mais recente seja válido
            Ativacao.objects.filter(user=user).delete()
            
            # Cria um novo token de ativação
            ativacao = Ativacao.objects.create(user=user)
            
            # Envia o e-mail de confirmação
            enviar_email_com_template(
                request,
                subject='Confirme seu Cadastro no Raio-X da Aprovação',
                template_name='usuarios/email_confirmacao.html',
                context={'user': user, 'token': ativacao.token},
                recipient_list=[user.email]
            )
            
            messages.success(request, 'Um novo e-mail de ativação foi enviado para o seu endereço. Verifique sua caixa de entrada e spam.')
            return redirect('login')
            
        except User.DoesNotExist:
            messages.error(request, 'Nenhum usuário inativo encontrado com este e-mail.')
            return redirect('reenviar_ativacao')

    return render(request, 'usuarios/reenviar_ativacao.html')
# =======================================================================
# FIM DA ADIÇÃO
# =======================================================================