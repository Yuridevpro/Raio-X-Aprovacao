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
from gamificacao.models import ProfileStreak, ConquistaUsuario, Conquista, ProfileGamificacao
from gamificacao.services import calcular_xp_para_nivel # <-- NOVO IMPORT
from django.shortcuts import get_object_or_404
from gamificacao.models import ProfileStreak, ConquistaUsuario, Conquista, ProfileGamificacao, MetaDiariaUsuario
from gamificacao.services import calcular_xp_para_nivel, META_DIARIA_QUESTOES
from datetime import date
from gamificacao.models import RankingSemanal, RankingMensal
from gamificacao.models import Avatar, Borda
from gamificacao.services import _verificar_desbloqueio_recompensas

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
    Exibe a página de perfil do USUÁRIO LOGADO.
    Esta view agora simplesmente busca o perfil do usuário logado e chama
    a função auxiliar _get_profile_context para obter todos os dados.
    """
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Chama a função auxiliar para buscar todos os dados de gamificação
    context = _get_profile_context(user_profile)
    
    return render(request, 'usuarios/perfil.html', context)


@login_required
def visualizar_perfil(request, username):
    """
    Busca os dados de um USUÁRIO ESPECÍFICO pelo username e renderiza 
    o mesmo template de perfil.
    """
    user_alvo = get_object_or_404(User, username=username)
    
    # Redireciona para a URL de 'meu_perfil' se o usuário tentar ver o próprio perfil
    if user_alvo == request.user:
        return redirect('meu_perfil')
    
    user_profile = get_object_or_404(UserProfile, user=user_alvo)
    
    # Chama a mesma função auxiliar
    context = _get_profile_context(user_profile)

    return render(request, 'usuarios/perfil.html', context)


def _get_profile_context(user_profile):
    """
    Função auxiliar central que busca TODOS os dados de gamificação para um 
    determinado UserProfile e retorna um dicionário de contexto.
    """
    streak_data, _ = ProfileStreak.objects.get_or_create(user_profile=user_profile)
    gamificacao_data, _ = ProfileGamificacao.objects.get_or_create(user_profile=user_profile)
    
    meta_hoje, _ = MetaDiariaUsuario.objects.get_or_create(
        user_profile=user_profile,
        data=date.today()
    )
    progresso_meta_diaria_percentual = min((meta_hoje.questoes_resolvidas / META_DIARIA_QUESTOES * 100), 100)
    
    xp_proximo_nivel = calcular_xp_para_nivel(gamificacao_data.level)
    xp_nivel_anterior = calcular_xp_para_nivel(gamificacao_data.level - 1)
    total_xp_do_nivel = xp_proximo_nivel - xp_nivel_anterior
    xp_no_nivel_atual = gamificacao_data.xp - xp_nivel_anterior
    progresso_percentual_xp = (xp_no_nivel_atual / total_xp_do_nivel * 100) if total_xp_do_nivel > 0 else 0

    todas_as_conquistas = Conquista.objects.all().order_by('nome')
    conquistas_desbloqueadas_ids = list(ConquistaUsuario.objects.filter(
        user_profile=user_profile
    ).values_list('conquista_id', flat=True))

    # =======================================================================
    # NOVA LÓGICA PARA O HALL DA FAMA
    # =======================================================================
    trofeus_semanais = RankingSemanal.objects.filter(user_profile=user_profile, posicao__lte=3).order_by('-ano', '-semana')
    trofeus_mensais = RankingMensal.objects.filter(user_profile=user_profile, posicao__lte=3).order_by('-ano', '-mes')
    # =======================================================================

    return {
        'perfil_visualizado': user_profile,
        'streak_data': streak_data,
        'gamificacao_data': gamificacao_data,
        'xp_proximo_nivel': xp_proximo_nivel,
        'progresso_percentual': progresso_percentual_xp,
        'todas_as_conquistas': todas_as_conquistas,
        'conquistas_desbloqueadas_ids': conquistas_desbloqueadas_ids,
        'meta_hoje': meta_hoje,
        'meta_diaria_total': META_DIARIA_QUESTOES,
        'progresso_meta_diaria_percentual': progresso_meta_diaria_percentual,
        # =======================================================================
        # ENVIANDO OS DADOS DO HALL DA FAMA PARA O TEMPLATE
        # =======================================================================
        'trofeus_semanais': trofeus_semanais,
        'trofeus_mensais': trofeus_mensais,
    }
    
    
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


def _get_profile_context(user_profile):
    streak_data, _ = ProfileStreak.objects.get_or_create(user_profile=user_profile)
    gamificacao_data, _ = ProfileGamificacao.objects.get_or_create(user_profile=user_profile)
    
    # =======================================================================
    # BUSCANDO DADOS DA META DIÁRIA ATUAL
    # =======================================================================
    meta_hoje, _ = MetaDiariaUsuario.objects.get_or_create(
        user_profile=user_profile,
        data=date.today()
    )
    progresso_meta_percentual = (meta_hoje.questoes_resolvidas / META_DIARIA_QUESTOES * 100)
    # Garante que a barra não passe de 100%
    progresso_meta_percentual = min(progresso_meta_percentual, 100)
    # =======================================================================
    
    xp_proximo_nivel = calcular_xp_para_nivel(gamificacao_data.level)
    xp_nivel_anterior = calcular_xp_para_nivel(gamificacao_data.level - 1)
    
    total_xp_do_nivel = xp_proximo_nivel - xp_nivel_anterior
    xp_no_nivel_atual = gamificacao_data.xp - xp_nivel_anterior
    progresso_percentual = (xp_no_nivel_atual / total_xp_do_nivel * 100) if total_xp_do_nivel > 0 else 0

    todas_as_conquistas = Conquista.objects.all().order_by('nome')
    conquistas_desbloqueadas_ids = ConquistaUsuario.objects.filter(
        user_profile=user_profile
    ).values_list('conquista_id', flat=True)

    return {
        'perfil_visualizado': user_profile,
        'streak_data': streak_data,
        'gamificacao_data': gamificacao_data,
        'xp_proximo_nivel': xp_proximo_nivel,
        'progresso_percentual': progresso_percentual,
        'todas_as_conquistas': todas_as_conquistas,
        'conquistas_desbloqueadas_ids': list(conquistas_desbloqueadas_ids),
        # =======================================================================
        # ENVIANDO NOVOS DADOS DA META PARA O TEMPLATE
        # =======================================================================
        'meta_hoje': meta_hoje,
        'meta_diaria_total': META_DIARIA_QUESTOES,
        'progresso_meta_percentual': progresso_meta_percentual,
    }

@login_required
def colecao(request):
    """Exibe a coleção de avatares e bordas do usuário."""
    user_profile = request.user.userprofile
    
    # =======================================================================
    # ADIÇÃO: VERIFICAÇÃO PROATIVA DE RECOMPENSAS
    # Toda vez que o usuário visita a coleção, o sistema verifica se ele
    # cumpre os requisitos para qualquer recompensa existente.
    # =======================================================================
    _verificar_desbloqueio_recompensas(user_profile)
    
    # O resto da view continua normalmente, buscando os dados atualizados.
    todos_avatares = Avatar.objects.all()
    todas_bordas = Borda.objects.all()
    
    avatares_desbloqueados_ids = list(user_profile.avatares_desbloqueados.values_list('avatar_id', flat=True))
    bordas_desbloqueadas_ids = list(user_profile.bordas_desbloqueadas.values_list('borda_id', flat=True))
    
    context = {
        'todos_avatares': todos_avatares,
        'todas_bordas': todas_bordas,
        'avatares_desbloqueados_ids': avatares_desbloqueados_ids,
        'bordas_desbloqueadas_ids': bordas_desbloqueadas_ids,
        'avatar_equipado_id': user_profile.avatar_equipado_id,
        'borda_equipada_id': user_profile.borda_equipada_id,
    }
    return render(request, 'usuarios/colecao.html', context)


@login_required
def equipar_avatar(request, avatar_id):
    """
    Equipa ou desequipa um avatar.
    Se o avatar clicado já estiver equipado, ele será desequipado.
    Se for um avatar diferente, ele será equipado.
    """
    user_profile = request.user.userprofile
    avatar_para_equipar = get_object_or_404(Avatar, id=avatar_id)
    
    # Verifica se o usuário realmente possui o avatar
    if not user_profile.avatares_desbloqueados.filter(avatar=avatar_para_equipar).exists():
        messages.error(request, 'Você ainda não desbloqueou este avatar.')
        return redirect('colecao')

    # Lógica de "Toggle": Se já está equipado, desequipa. Senão, equipa.
    if user_profile.avatar_equipado == avatar_para_equipar:
        user_profile.avatar_equipado = None
        messages.success(request, f'Avatar "{avatar_para_equipar.nome}" desequipado.')
    else:
        user_profile.avatar_equipado = avatar_para_equipar
        messages.success(request, f'Avatar "{avatar_para_equipar.nome}" equipado com sucesso!')
        
    user_profile.save()
    return redirect('colecao')

@login_required
def equipar_borda(request, borda_id):
    """ Equipa ou desequipa uma borda, com a mesma lógica de toggle. """
    user_profile = request.user.userprofile
    borda_para_equipar = get_object_or_404(Borda, id=borda_id)

    if not user_profile.bordas_desbloqueadas.filter(borda=borda_para_equipar).exists():
        messages.error(request, 'Você ainda não desbloqueou esta borda.')
        return redirect('colecao')

    if user_profile.borda_equipada == borda_para_equipar:
        user_profile.borda_equipada = None
        messages.success(request, f'Borda "{borda_para_equipar.nome}" desequipada.')
    else:
        user_profile.borda_equipada = borda_para_equipar
        messages.success(request, f'Borda "{borda_para_equipar.nome}" equipada com sucesso!')
    
    user_profile.save()
    return redirect('colecao')
