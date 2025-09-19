# usuarios/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import UserProfile, Ativacao, PasswordResetToken
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings
from questoes.models import Questao
from gestao.views import criar_log
from gestao.models import LogAtividade
from .utils import enviar_email_com_template
from django.db import transaction
from datetime import date

# --- Imports de Gamificação Corrigidos ---
from gamificacao.models import (
    ProfileStreak, ConquistaUsuario, Conquista, ProfileGamificacao, 
    MetaDiariaUsuario, RankingSemanal, RankingMensal, Avatar, Borda, 
    Banner, GamificationSettings  # <-- MUDANÇA: Importando o modelo de configurações
)
from gamificacao.services import (
    calcular_xp_para_nivel, 
    _verificar_desbloqueio_recompensas
)
from questoes.utils import paginar_itens


# =======================================================================
# VIEWS DE AUTENTICAÇÃO
# =======================================================================

@transaction.atomic
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

        try:
            user_existente = User.objects.get(email=email)
            if not user_existente.is_active:
                user_existente.delete() 
            else:
                messages.error(request, 'Este e-mail já está em uso por uma conta ativa.')
                return redirect('cadastro')
        except User.DoesNotExist:
            pass

        try:
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
            
            messages.success(request, 'Cadastro realizado! Um e-mail de confirmação foi enviado.')
            return redirect('login')

        except Exception as e:
            messages.error(request, f'Ocorreu um erro inesperado durante o cadastro. Nenhuma conta foi criada.')
            print(f"Erro de cadastro: {e}") 
            return redirect('cadastro')

    return render(request, 'usuarios/cadastro.html')


def confirmar_email(request, token):
    try:
        ativacao = Ativacao.objects.get(token=token)
        if ativacao.is_expired():
            messages.error(request, 'Link de ativação expirado. Tente se cadastrar novamente.')
            ativacao.user.delete()
            return redirect('cadastro')
            
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
            user_obj = User.objects.get(email=email)
            if not user_obj.is_active:
                messages.warning(request, 'Sua conta ainda não foi ativada. Verifique seu e-mail.')
                return redirect('login')
        except User.DoesNotExist:
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
            
            messages.success(request, 'Um e-mail com instruções foi enviado.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'Não foi encontrado um usuário com este e-mail.')
    return render(request, 'usuarios/esqueceu_senha.html')

def resetar_senha(request, token):
    try:
        token_obj = PasswordResetToken.objects.get(token=token)
        if token_obj.is_expired():
            messages.error(request, 'Link de redefinição expirado.')
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
                messages.success(request, 'Sua senha foi redefinida com sucesso!')
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

# =======================================================================
# VIEWS DE PERFIL E CONTA
# =======================================================================

@login_required
def meu_perfil(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    context = _get_profile_context(user_profile)
    return render(request, 'usuarios/perfil.html', context)

@login_required
def visualizar_perfil(request, username):
    user_alvo = get_object_or_404(User, username=username)
    if user_alvo == request.user:
        return redirect('meu_perfil')
    
    user_profile = get_object_or_404(UserProfile, user=user_alvo)
    context = _get_profile_context(user_profile)
    return render(request, 'usuarios/perfil.html', context)

def _get_profile_context(user_profile):
    """
    Função auxiliar que busca TODOS os dados de gamificação e perfil.
    """
    # <-- MUDANÇA: Carrega as configurações de gamificação do banco de dados
    settings = GamificationSettings.load()

    streak_data, _ = ProfileStreak.objects.get_or_create(user_profile=user_profile)
    gamificacao_data, _ = ProfileGamificacao.objects.get_or_create(user_profile=user_profile)
    
    meta_hoje, _ = MetaDiariaUsuario.objects.get_or_create(
        user_profile=user_profile,
        data=date.today()
    )
    
    # <-- MUDANÇA: Usa a configuração do banco de dados (settings) em vez da constante
    if settings.meta_diaria_questoes > 0:
        progresso_meta_diaria_percentual = min((meta_hoje.questoes_resolvidas / settings.meta_diaria_questoes * 100), 100)
    else:
        progresso_meta_diaria_percentual = 0

    xp_proximo_nivel = calcular_xp_para_nivel(gamificacao_data.level)
    xp_nivel_anterior = calcular_xp_para_nivel(gamificacao_data.level - 1)
    total_xp_do_nivel = xp_proximo_nivel - xp_nivel_anterior
    xp_no_nivel_atual = gamificacao_data.xp - xp_nivel_anterior
    progresso_percentual_xp = (xp_no_nivel_atual / total_xp_do_nivel * 100) if total_xp_do_nivel > 0 else 0

    todas_as_conquistas = Conquista.objects.all().order_by('nome')
    conquistas_desbloqueadas_ids = list(ConquistaUsuario.objects.filter(
        user_profile=user_profile
    ).values_list('conquista_id', flat=True))

    trofeus_semanais = RankingSemanal.objects.filter(user_profile=user_profile, posicao__lte=3).order_by('-ano', '-semana')
    trofeus_mensais = RankingMensal.objects.filter(user_profile=user_profile, posicao__lte=3).order_by('-ano', '-mes')

    return {
        'perfil_visualizado': user_profile,
        'streak_data': streak_data,
        'gamificacao_data': gamificacao_data,
        'xp_proximo_nivel': xp_proximo_nivel,
        'progresso_percentual': progresso_percentual_xp,
        'todas_as_conquistas': todas_as_conquistas,
        'conquistas_desbloqueadas_ids': conquistas_desbloqueadas_ids,
        'meta_hoje': meta_hoje,
        # <-- MUDANÇA: Usa a configuração do banco de dados (settings)
        'meta_diaria_total': settings.meta_diaria_questoes, 
        'progresso_meta_diaria_percentual': progresso_meta_diaria_percentual,
        'trofeus_semanais': trofeus_semanais,
        'trofeus_mensais': trofeus_mensais,
    }
    
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
            return redirect('meu_perfil') 
            
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
        if user.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
            messages.error(request, 'Ação negada: Você é o único superusuário restante.')
            return redirect('editar_perfil')

        username = user.username
        criar_log(
            ator=user, acao=LogAtividade.Acao.USUARIO_DELETADO, alvo=None,
            detalhes={'usuario_deletado': username, 'motivo': 'Usuário excluiu a própria conta.'}
        )
        
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
                messages.info(request, 'Esta conta já está ativa.')
                return redirect('login')
            
            Ativacao.objects.filter(user=user).delete()
            ativacao = Ativacao.objects.create(user=user)
            
            enviar_email_com_template(
                request,
                subject='Confirme seu Cadastro no Raio-X da Aprovação',
                template_name='usuarios/email_confirmacao.html',
                context={'user': user, 'token': ativacao.token},
                recipient_list=[user.email]
            )
            
            messages.success(request, 'Um novo e-mail de ativação foi enviado.')
            return redirect('login')
            
        except User.DoesNotExist:
            messages.error(request, 'Nenhum usuário inativo encontrado com este e-mail.')
            return redirect('reenviar_ativacao')

    return render(request, 'usuarios/reenviar_ativacao.html')

# =======================================================================
# VIEWS DE COLEÇÃO
# =======================================================================

@login_required
def colecao_avatares(request):
    user_profile = request.user.userprofile
    _verificar_desbloqueio_recompensas(user_profile)
    
    base_queryset = Avatar.objects.all()
    filtro_raridade = request.GET.get('raridade')
    if filtro_raridade:
        base_queryset = base_queryset.filter(raridade=filtro_raridade)

    page_obj, page_numbers, per_page = paginar_itens(request, base_queryset, items_per_page=12)
    
    context = {
        'user_profile': user_profile,
        'itens': page_obj,
        'desbloqueados_ids': list(user_profile.avatares_desbloqueados.values_list('avatar_id', flat=True)),
        'equipado_id': user_profile.avatar_equipado_id,
        'tipo_item': 'avatar',
        'titulo_pagina': 'Meus Avatares',
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'raridade_choices': Avatar.Raridade.choices,
        'filtro_raridade_ativo': filtro_raridade,
    }
    return render(request, 'usuarios/colecao_listagem.html', context)


@login_required
def colecao_bordas(request):
    user_profile = request.user.userprofile
    _verificar_desbloqueio_recompensas(user_profile)

    base_queryset = Borda.objects.all()
    filtro_raridade = request.GET.get('raridade')
    if filtro_raridade:
        base_queryset = base_queryset.filter(raridade=filtro_raridade)

    page_obj, page_numbers, per_page = paginar_itens(request, base_queryset, items_per_page=12)

    context = {
        'user_profile': user_profile,
        'itens': page_obj,
        'desbloqueados_ids': list(user_profile.bordas_desbloqueadas.values_list('borda_id', flat=True)),
        'equipado_id': user_profile.borda_equipada_id,
        'tipo_item': 'borda',
        'titulo_pagina': 'Minhas Bordas',
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'raridade_choices': Borda.Raridade.choices,
        'filtro_raridade_ativo': filtro_raridade,
    }
    return render(request, 'usuarios/colecao_listagem.html', context)


@login_required
def colecao_banners(request):
    user_profile = request.user.userprofile
    _verificar_desbloqueio_recompensas(user_profile)

    base_queryset = Banner.objects.all()
    filtro_raridade = request.GET.get('raridade')
    if filtro_raridade:
        base_queryset = base_queryset.filter(raridade=filtro_raridade)

    page_obj, page_numbers, per_page = paginar_itens(request, base_queryset, items_per_page=8)

    context = {
        'user_profile': user_profile,
        'itens': page_obj,
        'desbloqueados_ids': list(user_profile.banners_desbloqueados.values_list('banner_id', flat=True)),
        'equipado_id': user_profile.banner_equipado_id,
        'tipo_item': 'banner',
        'titulo_pagina': 'Meus Banners',
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'raridade_choices': Banner.Raridade.choices,
        'filtro_raridade_ativo': filtro_raridade,
    }
    return render(request, 'usuarios/colecao_listagem.html', context)

# =======================================================================
# VIEWS DE EQUIPAR ITENS
# =======================================================================

@login_required
def equipar_avatar(request, avatar_id):
    user_profile = request.user.userprofile
    avatar_para_equipar = get_object_or_404(Avatar, id=avatar_id)
    
    if not user_profile.avatares_desbloqueados.filter(avatar=avatar_para_equipar).exists():
        messages.error(request, 'Você ainda não desbloqueou este avatar.')
        return redirect('colecao_avatares')

    if user_profile.avatar_equipado == avatar_para_equipar:
        user_profile.avatar_equipado = None
        user_profile.borda_equipada = None
        messages.success(request, f'Avatar "{avatar_para_equipar.nome}" desequipado.')
    else:
        user_profile.avatar_equipado = avatar_para_equipar
        messages.success(request, f'Avatar "{avatar_para_equipar.nome}" equipado com sucesso!')
        
    user_profile.save()
    return redirect('colecao_avatares')

@login_required
def equipar_borda(request, borda_id):
    user_profile = request.user.userprofile
    borda_para_equipar = get_object_or_404(Borda, id=borda_id)

    if not user_profile.avatar_equipado:
        messages.error(request, 'Você precisa equipar um avatar antes de poder usar uma borda.')
        return redirect('colecao_bordas')

    if not user_profile.bordas_desbloqueadas.filter(borda=borda_para_equipar).exists():
        messages.error(request, 'Você ainda não desbloqueou esta borda.')
        return redirect('colecao_bordas')

    if user_profile.borda_equipada == borda_para_equipar:
        user_profile.borda_equipada = None
        messages.success(request, f'Borda "{borda_para_equipar.nome}" desequipada.')
    else:
        user_profile.borda_equipada = borda_para_equipar
        messages.success(request, f'Borda "{borda_para_equipar.nome}" equipada com sucesso!')
    
    user_profile.save()
    return redirect('colecao_bordas')


@login_required
def equipar_banner(request, banner_id):
    user_profile = request.user.userprofile
    banner_para_equipar = get_object_or_404(Banner, id=banner_id)

    if not user_profile.banners_desbloqueados.filter(banner=banner_para_equipar).exists():
        messages.error(request, 'Você ainda não desbloqueou este banner.')
        return redirect('colecao_banners')

    if user_profile.banner_equipado == banner_para_equipar:
        user_profile.banner_equipado = None
        messages.success(request, f'Banner "{banner_para_equipar.nome}" desequipado.')
    else:
        user_profile.banner_equipado = banner_para_equipar
        messages.success(request, f'Banner "{banner_para_equipar.nome}" equipado com sucesso!')
    
    user_profile.save()
    return redirect('colecao_banners')


@login_required
def desequipar_item(request, tipo_item):
    user_profile = request.user.userprofile
    
    redirect_url = 'meu_perfil' # Default redirect
    if tipo_item == 'avatar':
        user_profile.avatar_equipado = None
        user_profile.borda_equipada = None
        messages.success(request, 'Avatar desequipado com sucesso.')
        redirect_url = 'colecao_avatares'
    elif tipo_item == 'borda':
        user_profile.borda_equipada = None
        messages.success(request, 'Borda desequipada com sucesso.')
        redirect_url = 'colecao_bordas'
    elif tipo_item == 'banner':
        user_profile.banner_equipado = None
        messages.success(request, 'Banner desequipado com sucesso.')
        redirect_url = 'colecao_banners'
    else:
        messages.error(request, 'Tipo de item inválido.')

    user_profile.save()
    return redirect(redirect_url)