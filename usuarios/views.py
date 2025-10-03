# usuarios/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
# =======================================================================
# IMPORTAÇÕES REORDENADAS PARA RESOLVER O ERRO
# =======================================================================
# 1. Imports de Gamificação vêm PRIMEIRO, para que os modelos sejam conhecidos.
from gamificacao.models import (
    RecompensaPendente, TrilhaDeConquistas, ConquistaUsuario, ProfileStreak, 
    Conquista, ProfileGamificacao, MetaDiariaUsuario, RankingSemanal, 
    RankingMensal, Avatar, Borda, Banner, GamificationSettings,
    AvatarUsuario, BordaUsuario, BannerUsuario
)
from gamificacao.services import (
    calcular_xp_para_nivel, 
    _verificar_desbloqueio_recompensas,
    _obter_valor_variavel
)
# 2. Agora, importamos UserProfile, que DEPENDE dos modelos de gamificação.
from .models import UserProfile, Ativacao, PasswordResetToken
from simulados.models import SessaoSimulado # ✅ Adicionado

# =======================================================================
# FIM DA CORREÇÃO
# =======================================================================
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings
from questoes.models import Questao
from gestao.utils import criar_log
from gestao.models import LogAtividade
from .utils import enviar_email_com_template
from django.db import transaction
from datetime import date
from questoes.utils import paginar_itens
from questoes.models import Questao # Adicione esta importação no topo

from django.db.models import Prefetch, Count, Q, F, Window, Case, When, Value, IntegerField
from django.db.models.functions import Rank
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
            
            messages.success(request, 'Cadastro realizado! Um e-mail de confirmação foi enviado. Verifique sua caixa de entrada e principalmente a caixa de Spam.')
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
            
            messages.success(request, 'Um e-mail com instruções foi enviado. Verifique sua caixa de entrada e principalmente a caixa de Spam.')
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
    """
    Renderiza a página inicial com estatísticas dinâmicas para
    mostrar a escala e atividade da plataforma.
    """
    total_questoes = Questao.objects.count()
    total_usuarios = User.objects.filter(is_active=True).count()
    total_simulados_concluidos = SessaoSimulado.objects.filter(finalizado=True).count()

    context = {
        'total_questoes': total_questoes,
        'total_usuarios': total_usuarios,
        'total_simulados_concluidos': total_simulados_concluidos,
    }
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
    settings = GamificationSettings.load()

    streak_data, _ = ProfileStreak.objects.get_or_create(user_profile=user_profile)
    gamificacao_data, _ = ProfileGamificacao.objects.get_or_create(user_profile=user_profile)
    
    meta_hoje, _ = MetaDiariaUsuario.objects.get_or_create(
        user_profile=user_profile,
        data=date.today()
    )
    
    if settings.meta_diaria_questoes > 0:
        progresso_meta_diaria_percentual = min((meta_hoje.questoes_resolvidas / settings.meta_diaria_questoes * 100), 100)
    else:
        progresso_meta_diaria_percentual = 0

    xp_proximo_nivel = calcular_xp_para_nivel(gamificacao_data.level)
    xp_nivel_anterior = calcular_xp_para_nivel(gamificacao_data.level - 1)
    total_xp_do_nivel = xp_proximo_nivel - xp_nivel_anterior
    xp_no_nivel_atual = gamificacao_data.xp - xp_nivel_anterior
    progresso_percentual_xp = (xp_no_nivel_atual / total_xp_do_nivel * 100) if total_xp_do_nivel > 0 else 0

    # =======================================================================
    # INÍCIO DA ALTERAÇÃO: Passando os objetos de conquista desbloqueados
    # =======================================================================
    conquistas_desbloqueadas = Conquista.objects.filter(
        conquistausuario__user_profile=user_profile
    ).order_by('nome')
    # =======================================================================
    # FIM DA ALTERAÇÃO
    # =======================================================================

    trofeus_semanais = RankingSemanal.objects.filter(user_profile=user_profile, posicao__lte=3).order_by('-ano', '-semana')
    trofeus_mensais = RankingMensal.objects.filter(user_profile=user_profile, posicao__lte=3).order_by('-ano', '-mes')

    return {
        'perfil_visualizado': user_profile,
        'streak_data': streak_data,
        'gamificacao_data': gamificacao_data,
        'xp_proximo_nivel': xp_proximo_nivel,
        'progresso_percentual': progresso_percentual_xp,
        'conquistas_desbloqueadas': conquistas_desbloqueadas, # Nome da variável alterado para clareza
        'meta_hoje': meta_hoje,
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
            
            messages.success(request, 'Um novo e-mail de ativação foi enviado. Verifique sua caixa de entrada e principalmente a caixa de Spam.')
            return redirect('login')
            
        except User.DoesNotExist:
            messages.error(request, 'Nenhum usuário inativo encontrado com este e-mail.')
            return redirect('reenviar_ativacao')

    return render(request, 'usuarios/reenviar_ativacao.html')

# =======================================================================
# VIEWS DE COLEÇÃO
# =======================================================================

def _grant_all_rewards_to_staff(user_profile, Model, M2M_Manager):
    """Concede todas as recompensas de um tipo a um membro da equipe."""
    if not user_profile.user.is_staff:
        return
    
    todos_os_itens = Model.objects.all()
    for item in todos_os_itens:
        m2m_field_name = Model.__name__.lower()
        M2M_Manager.get_or_create(user_profile=user_profile, **{m2m_field_name: item})


def _get_colecao_context(request, Model, user_profile, tipo_item, titulo_pagina):
    """
    Função auxiliar para obter o contexto de qualquer página de coleção (Avatares, Bordas, Banners),
    já com lógica de filtro, ordenação e paginação.
    """
    _verificar_desbloqueio_recompensas(user_profile)
    
    related_name_map = {
        'avatar': 'avatares_desbloqueados',
        'borda': 'bordas_desbloqueadas',
        'banner': 'banners_desbloqueados',
    }
    related_manager_name = related_name_map.get(tipo_item)
    if not related_manager_name:
        return {} 
    
    M2M_Manager = getattr(user_profile, related_manager_name)
    
    if user_profile.user.is_staff:
        todos_os_itens = Model.objects.all()
        for item in todos_os_itens:
            M2M_Manager.model.objects.get_or_create(user_profile=user_profile, **{f'{tipo_item}_id': item.id})

    base_queryset = Model.objects.all()
    
    filtro_raridade = request.GET.get('raridade')
    if filtro_raridade:
        base_queryset = base_queryset.filter(raridade=filtro_raridade)

    desbloqueados_ids = list(M2M_Manager.values_list(f'{tipo_item}_id', flat=True))

    unlocked_first_order = Case(
        When(pk__in=desbloqueados_ids, then=Value(0)),
        default=Value(1),
        output_field=IntegerField()
    )

    rarity_order = Case(
        *[When(raridade=rarity_tuple[0], then=Value(i)) for i, rarity_tuple in enumerate(Model.Raridade.choices)],
        output_field=IntegerField()
    )
    
    itens_ordenados = base_queryset.annotate(
        is_unlocked=unlocked_first_order,
        rarity_order=rarity_order
    ).order_by('is_unlocked', '-rarity_order', 'nome')

    page_obj, page_numbers, per_page = paginar_itens(request, itens_ordenados, items_per_page=10)
    
    # =======================================================================
    # ✅ INÍCIO DA CORREÇÃO: Lógica para pegar o ID do item equipado
    # =======================================================================
    equipado_id = None
    if tipo_item == 'borda':
        # Trata o caso especial de 'borda_equipada' (feminino)
        if user_profile.borda_equipada:
            equipado_id = user_profile.borda_equipada.id
    else:
        # Usa a lógica dinâmica para os outros casos (avatar, banner)
        equipado_obj = getattr(user_profile, f'{tipo_item}_equipado', None)
        if equipado_obj:
            equipado_id = equipado_obj.id
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================

    return {
        'user_profile': user_profile,
        'itens': page_obj,
        'desbloqueados_ids': desbloqueados_ids,
        'equipado_id': equipado_id, # Agora esta variável terá o valor correto para bordas
        'tipo_item': tipo_item,
        'titulo_pagina': titulo_pagina,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'raridade_choices': Model.Raridade.choices,
        'filtro_raridade_ativo': filtro_raridade,
    }

@login_required
def colecao_avatares(request):
    context = _get_colecao_context(request, Avatar, request.user.userprofile, 'avatar', 'Meus Avatares')
    return render(request, 'usuarios/colecao_listagem.html', context)

@login_required
def colecao_bordas(request):
    context = _get_colecao_context(request, Borda, request.user.userprofile, 'borda', 'Minhas Bordas')
    return render(request, 'usuarios/colecao_listagem.html', context)

@login_required
def colecao_banners(request):
    context = _get_colecao_context(request, Banner, request.user.userprofile, 'banner', 'Meus Banners')
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
    
    redirect_url = 'meu_perfil'
    if tipo_item == 'avatar':
        user_profile.avatar_equipado = None
        user_profile.borda_equipada = None
        messages.success(request, 'Avatar e borda desequipados com sucesso.')
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


@login_required
def caixa_de_recompensas(request):
    """ Exibe a página com os prêmios pendentes do usuário para resgate. """
    user_profile = request.user.userprofile
    
    _verificar_desbloqueio_recompensas(user_profile)
    
    # =======================================================================
    # ✅ INÍCIO DA CORREÇÃO: Contexto de paginação completo
    # =======================================================================
    # 1. Obtemos o queryset completo de recompensas, ordenado.
    recompensas_queryset = RecompensaPendente.objects.filter(
        user_profile=user_profile, 
        resgatado_em__isnull=True
    ).prefetch_related('recompensa').order_by('-data_ganho')

    # 2. Usamos a função auxiliar para paginar o queryset.
    page_obj, page_numbers, per_page = paginar_itens(request, recompensas_queryset, items_per_page=10)

    # 3. ATUALIZAÇÃO CRÍTICA: Adicionamos TODAS as variáveis de paginação ao contexto.
    context = {
        'recompensas_pendentes': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,  # <-- ESTA LINHA ESTAVA FALTANDO
        'per_page': per_page,          # <-- Adicionado por consistência
        'titulo_pagina': 'Câmara dos Tesouros',
        'active_tab': 'caixa_de_recompensas'
    }
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================
    
    return render(request, 'usuarios/caixa_de_recompensas.html', context)



from django.db.models import Prefetch # ✅ LINHA ADICIONADA PARA CORRIGIR O ERRO

@login_required
def trilhas_de_conquistas(request):
    """
    Exibe as trilhas de conquistas com lógica de agrupamento aprimorada,
    incluindo o nome da série e múltiplos progressos para exibição no template.
    """
    user_profile = request.user.userprofile
    trilhas = TrilhaDeConquistas.objects.prefetch_related(
        Prefetch('conquistas', queryset=Conquista.objects.select_related('serie')),
        'conquistas__pre_requisitos',
        'conquistas__condicoes__variavel'
    ).order_by('ordem', 'nome')
    conquistas_usuario_ids = set(user_profile.conquistas_usuario.values_list('conquista_id', flat=True))

    reward_ids = {'avatares': set(), 'bordas': set(), 'banners': set()}
    for trilha in trilhas:
        for conquista in trilha.conquistas.all():
            if conquista.recompensas:
                reward_ids['avatares'].update(conquista.recompensas.get('avatares', []))
                reward_ids['bordas'].update(conquista.recompensas.get('bordas', []))
                reward_ids['banners'].update(conquista.recompensas.get('banners', []))

    avatars_map = {a.id: a for a in Avatar.objects.filter(id__in=reward_ids['avatares'])}
    bordas_map = {b.id: b for b in Borda.objects.filter(id__in=reward_ids['bordas'])}
    banners_map = {b.id: b for b in Banner.objects.filter(id__in=reward_ids['banners'])}

    for trilha in trilhas:
        conquistas_em_serie = [c for c in trilha.conquistas.all() if c.serie]
        conquistas_individuais = [c for c in trilha.conquistas.all() if not c.serie]
        
        series_agrupadas = {}
        for c in conquistas_em_serie:
            if c.serie.id not in series_agrupadas:
                series_agrupadas[c.serie.id] = {'serie_obj': c.serie, 'conquistas': []}
            series_agrupadas[c.serie.id]['conquistas'].append(c)

        trilha.sequencias_com_titulo = []
        for serie_id, dados_serie in series_agrupadas.items():
            conquistas_ordenadas = sorted(dados_serie['conquistas'], key=lambda x: x.ordem_na_serie)
            trilha.sequencias_com_titulo.append({
                'titulo': dados_serie['serie_obj'].nome,
                'descricao': dados_serie['serie_obj'].descricao,
                'conquistas': conquistas_ordenadas
            })

        trilha.conquistas_individuais = conquistas_individuais

        for conquista in trilha.conquistas.all():
            conquista.unlock_conditions_humanized = []
            
            if conquista.is_secreta and conquista.id not in conquistas_usuario_ids:
                conquista.status = 'hidden'
            elif conquista.id in conquistas_usuario_ids:
                conquista.status = 'unlocked'
            else:
                pre_req_ids = set(p.id for p in conquista.pre_requisitos.all())
                if pre_req_ids.issubset(conquistas_usuario_ids):
                    conquista.status = 'available'
                    
                    # ✅ INÍCIO DA ALTERAÇÃO: Lógica para múltiplos progressos
                    conquista.progress_bars = []
                    # ✅ FIM DA ALTERAÇÃO

                    for condicao in conquista.condicoes.all():
                        cond_text = f"{condicao.variavel.nome_exibicao} {condicao.get_operador_display().lower()} {condicao.valor}"
                        conquista.unlock_conditions_humanized.append(cond_text)
                    
                        # ✅ INÍCIO DA ALTERAÇÃO: Calcula o progresso para cada condição
                        valor_atual = _obter_valor_variavel(user_profile, condicao.variavel.chave, condicao.contexto_json)
                        valor_meta = condicao.valor
                        if valor_meta > 0:
                            progresso = min((valor_atual / valor_meta) * 100, 100)
                            conquista.progress_bars.append({
                                'label': condicao.variavel.nome_exibicao,
                                'atual': int(valor_atual), 
                                'meta': valor_meta, 
                                'percentual': int(progresso)
                            })
                        # ✅ FIM DA ALTERAÇÃO
                else:
                    conquista.status = 'locked'
                    for pre_req in conquista.pre_requisitos.all():
                        if pre_req.id not in conquistas_usuario_ids:
                            conquista.unlock_conditions_humanized.append(f"Desbloquear a conquista '{pre_req.nome}'")
            
            conquista.recompensas_detalhadas = []
            if conquista.recompensas:
                for r_type, r_map in [('avatares', avatars_map), ('bordas', bordas_map), ('banners', banners_map)]:
                    for r_id in conquista.recompensas.get(r_type, []):
                        if r_id in r_map:
                            conquista.recompensas_detalhadas.append(r_map[r_id])

    context = { 'trilhas': trilhas, 'active_tab': 'trilhas_de_conquistas' }
    return render(request, 'usuarios/trilhas_de_conquistas.html', context)