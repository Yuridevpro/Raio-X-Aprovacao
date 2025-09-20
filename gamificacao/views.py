# gamificacao/views.py (ARQUIVO COMPLETO E CORRIGIDO)

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F, Window
from django.db.models.functions import Rank
from django.utils import timezone
from datetime import date, timedelta
from itertools import chain
import json
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_POST

# Utils e Services
from questoes.utils import paginar_itens
from .services import verificar_e_gerar_rankings

# Modelos
from usuarios.models import UserProfile
from .models import (
    RankingSemanal, RankingMensal, Campanha, Avatar, Borda, Banner,
    RecompensaPendente,
    # =======================================================================
    # INÍCIO DA CORREÇÃO: ADICIONANDO AS IMPORTAÇÕES FALTANTES
    # =======================================================================
    AvatarUsuario, BordaUsuario, BannerUsuario, RecompensaUsuario
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================
)


@login_required
def ranking(request):
    """
    Exibe a página de ranking dos usuários, com abas para "Geral", "Semanal" e "Mensal".
    Busca os dados apropriados para cada período e exibe as recompensas em disputa.
    """
    verificar_e_gerar_rankings()

    periodo = request.GET.get('periodo', 'geral')
    queryset_ranqueado = UserProfile.objects.none()
    posicao_usuario_logado = None

    if periodo == 'semanal':
        titulo_ranking = "Ranking Semanal"
        ultima_semana = RankingSemanal.objects.order_by('-ano', '-semana').values('ano', 'semana').first()
        if ultima_semana:
            queryset_ranqueado = RankingSemanal.objects.filter(
                ano=ultima_semana['ano'], semana=ultima_semana['semana']
            ).select_related(
                'user_profile__user', 'user_profile__streak_data'
            ).annotate(
                rank=F('posicao'), nome=F('user_profile__nome'), sobrenome=F('user_profile__sobrenome'),
                user=F('user_profile__user'), total_acertos=F('acertos_periodo'),
                total_respostas=F('respostas_periodo'), streak_data=F('user_profile__streak_data')
            ).order_by('posicao')
            posicao_usuario_logado = queryset_ranqueado.filter(user_profile__user=request.user).first()

    elif periodo == 'mensal':
        titulo_ranking = "Ranking Mensal"
        ultimo_mes = RankingMensal.objects.order_by('-ano', '-mes').values('ano', 'mes').first()
        if ultimo_mes:
            queryset_ranqueado = RankingMensal.objects.filter(
                ano=ultimo_mes['ano'], mes=ultimo_mes['mes']
            ).select_related(
                'user_profile__user', 'user_profile__streak_data'
            ).annotate(
                rank=F('posicao'), nome=F('user_profile__nome'), sobrenome=F('user_profile__sobrenome'),
                user=F('user_profile__user'), total_acertos=F('acertos_periodo'),
                total_respostas=F('respostas_periodo'), streak_data=F('user_profile__streak_data')
            ).order_by('posicao')
            posicao_usuario_logado = queryset_ranqueado.filter(user_profile__user=request.user).first()

    else: # Período 'geral'
        titulo_ranking = "Ranking Geral"
        base_queryset = UserProfile.objects.filter(
            user__is_active=True, user__is_staff=False
        ).select_related('user', 'streak_data').annotate(
            total_respostas=Count('user__respostausuario'),
            total_acertos=Count('user__respostausuario', filter=Q(user__respostausuario__foi_correta=True))
        ).filter(total_respostas__gt=0)
        
        ordenacao = ('-total_acertos', '-streak_data__current_streak')
        queryset_ranqueado = base_queryset.annotate(
            rank=Window(expression=Rank(), order_by=[F(field[1:]).desc() if field.startswith('-') else F(field).asc() for field in ordenacao])
        ).order_by(*ordenacao)
        posicao_usuario_logado = queryset_ranqueado.filter(user=request.user).first()

    recompensas_em_disputa = []
    gatilho_campanha = None
    agora = timezone.now()

    if periodo == 'semanal':
        gatilho_campanha = Campanha.Gatilho.RANKING_SEMANAL_CONCLUIDO
    elif periodo == 'mensal':
        gatilho_campanha = Campanha.Gatilho.RANKING_MENSAL_CONCLUIDO

    if gatilho_campanha:
        campanhas_ativas = Campanha.objects.filter(
            ativo=True, gatilho=gatilho_campanha,
            data_inicio__lte=agora
        ).filter(Q(data_fim__gte=agora) | Q(data_fim__isnull=True))
        
        recompensas_ids = {'avatares': set(), 'bordas': set(), 'banners': set()}
        for campanha in campanhas_ativas:
            for grupo in campanha.grupos_de_condicoes:
                recompensas_ids['avatares'].update(grupo.get('avatares', []))
                recompensas_ids['bordas'].update(grupo.get('bordas', []))
                recompensas_ids['banners'].update(grupo.get('banners', []))
        
        avatares = Avatar.objects.filter(id__in=recompensas_ids['avatares'])
        bordas = Borda.objects.filter(id__in=recompensas_ids['bordas'])
        banners = Banner.objects.filter(id__in=recompensas_ids['banners'])
        
        recompensas_em_disputa = sorted(list(chain(avatares, bordas, banners)), key=lambda x: x.raridade)
    
    page_obj, page_numbers, per_page = paginar_itens(request, queryset_ranqueado, 25)

    context = {
        'ranking_list': page_obj, 'paginated_object': page_obj, 'page_numbers': page_numbers,
        'per_page': per_page, 'posicao_usuario_logado': posicao_usuario_logado,
        'recompensas_em_disputa': recompensas_em_disputa, 'periodo_ativo': periodo,
        'titulo_ranking': titulo_ranking,
    }
    return render(request, 'gamificacao/ranking.html', context)


@login_required
def loja(request):
    """ Exibe a Loja de Recompensas com itens compráveis. """
    user_profile = request.user.userprofile
    avatares = Avatar.objects.filter(tipo_desbloqueio='LOJA', preco_moedas__gt=0)
    bordas = Borda.objects.filter(tipo_desbloqueio='LOJA', preco_moedas__gt=0)
    banners = Banner.objects.filter(tipo_desbloqueio='LOJA', preco_moedas__gt=0)
    todos_os_itens = sorted(list(chain(avatares, bordas, banners)), key=lambda item: item.preco_moedas)
    itens_possuidos_ids = {
        'Avatar': list(user_profile.avatares_desbloqueados.values_list('avatar_id', flat=True)),
        'Borda': list(user_profile.bordas_desbloqueados.values_list('borda_id', flat=True)),
        'Banner': list(user_profile.banners_desbloqueados.values_list('banner_id', flat=True)),
    }
    context = {
        'itens_loja': todos_os_itens,
        'itens_possuidos_ids': itens_possuidos_ids,
        'saldo_atual': user_profile.gamificacao_data.moedas,
    }
    return render(request, 'gamificacao/loja.html', context)


@login_required
@require_POST
@transaction.atomic
def comprar_item_ajax(request):
    """ Processa a compra de um item da loja via AJAX. """
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        item_tipo = data.get('item_tipo')

        ModelMap = {'Avatar': Avatar, 'Borda': Borda, 'Banner': Banner}
        Model = ModelMap.get(item_tipo)

        if not Model:
            return JsonResponse({'status': 'error', 'message': 'Tipo de item inválido.'}, status=400)
        
        item = get_object_or_404(Model, id=item_id, tipo_desbloqueio='LOJA')
        user_profile = request.user.userprofile
        gamificacao_data = user_profile.gamificacao_data

        if gamificacao_data.moedas < item.preco_moedas:
            return JsonResponse({'status': 'error', 'message': 'Você não tem moedas suficientes.'}, status=403)

        created = False
        if item_tipo == 'Avatar':
            _, created = AvatarUsuario.objects.get_or_create(user_profile=user_profile, avatar=item)
        elif item_tipo == 'Borda':
            _, created = BordaUsuario.objects.get_or_create(user_profile=user_profile, borda=item)
        elif item_tipo == 'Banner':
            _, created = BannerUsuario.objects.get_or_create(user_profile=user_profile, banner=item)
        
        if not created:
            return JsonResponse({'status': 'error', 'message': 'Você já possui este item.'}, status=409)

        # Se a criação foi bem-sucedida, deduz as moedas e registra a transação
        gamificacao_data.moedas -= item.preco_moedas
        gamificacao_data.save()
        
        # Cria um registro da recompensa para fins de log e histórico
        RecompensaUsuario.objects.create(
            user_profile=user_profile,
            recompensa=item,
            concedido_por=None # Indica que foi uma compra, não uma concessão manual
        )
        
        return JsonResponse({
            'status': 'success', 
            'message': f'"{item.nome}" comprado com sucesso!',
            'novo_saldo': gamificacao_data.moedas
        })

    except Exception as e:
        # Para depuração, é útil logar o erro no console do servidor
        print(f"Erro em comprar_item_ajax: {e}")
        return JsonResponse({'status': 'error', 'message': 'Ocorreu um erro inesperado.'}, status=500)


@login_required
@require_POST
@transaction.atomic
def resgatar_recompensa_ajax(request):
    """ Processa o resgate de uma recompensa pendente via AJAX. """
    try:
        data = json.loads(request.body)
        pendente_id = data.get('pendente_id')
        
        recompensa_pendente = get_object_or_404(
            RecompensaPendente,
            id=pendente_id,
            user_profile=request.user.userprofile,
            resgatado_em__isnull=True
        )

        sucesso = recompensa_pendente.resgatar()

        if sucesso:
            # Cria um registro da recompensa para fins de log e histórico
            RecompensaUsuario.objects.create(
                user_profile=request.user.userprofile,
                recompensa=recompensa_pendente.recompensa
            )
            return JsonResponse({
                'status': 'success', 
                'message': f'"{recompensa_pendente.recompensa.nome}" foi adicionado à sua coleção!'
            })
        else:
             return JsonResponse({'status': 'error', 'message': 'Não foi possível resgatar esta recompensa.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Ocorreu um erro inesperado.'}, status=500)