# gamificacao/views.py (ARQUIVO COMPLETO)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from usuarios.models import UserProfile
from django.db.models import Count, Q, F, Window, Prefetch
from django.db.models.functions import Rank
from questoes.utils import paginar_itens
from .services import verificar_e_gerar_rankings
from .models import RankingSemanal, RankingMensal, RegraRecompensa, Avatar, Borda, Banner
from django.utils import timezone
from datetime import date, timedelta
from itertools import chain

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

    # =======================================================================
    # LÓGICA DE SELEÇÃO DE DADOS BASEADA NO PERÍODO (COM CORREÇÃO)
    # =======================================================================

    if periodo == 'semanal':
        titulo_ranking = "Ranking Semanal"
        ultima_semana = RankingSemanal.objects.order_by('-ano', '-semana').values('ano', 'semana').first()
        if ultima_semana:
            queryset_ranqueado = RankingSemanal.objects.filter(
                ano=ultima_semana['ano'],
                semana=ultima_semana['semana']
            ).select_related(
                'user_profile__user', 'user_profile__streak_data'
            ).annotate(
                rank=F('posicao'),
                nome=F('user_profile__nome'),
                sobrenome=F('user_profile__sobrenome'),
                user=F('user_profile__user'),
                total_acertos=F('acertos_periodo'),
                total_respostas=F('respostas_periodo'),
                streak_data=F('user_profile__streak_data')
            ).order_by('posicao')
            
            # Filtro correto para RankingSemanal
            posicao_usuario_logado = queryset_ranqueado.filter(user_profile__user=request.user).first()

    elif periodo == 'mensal':
        titulo_ranking = "Ranking Mensal"
        ultimo_mes = RankingMensal.objects.order_by('-ano', '-mes').values('ano', 'mes').first()
        if ultimo_mes:
            queryset_ranqueado = RankingMensal.objects.filter(
                ano=ultimo_mes['ano'],
                mes=ultimo_mes['mes']
            ).select_related(
                'user_profile__user', 'user_profile__streak_data'
            ).annotate(
                rank=F('posicao'),
                nome=F('user_profile__nome'),
                sobrenome=F('user_profile__sobrenome'),
                user=F('user_profile__user'),
                total_acertos=F('acertos_periodo'),
                total_respostas=F('respostas_periodo'),
                streak_data=F('user_profile__streak_data')
            ).order_by('posicao')

            # Filtro correto para RankingMensal
            posicao_usuario_logado = queryset_ranqueado.filter(user_profile__user=request.user).first()

    else: # Período 'geral' é o padrão
        titulo_ranking = "Ranking Geral"
        base_queryset = UserProfile.objects.filter(
            user__is_active=True,
            user__is_staff=False
        ).select_related('user', 'streak_data').annotate(
            total_respostas=Count('user__respostausuario'),
            total_acertos=Count('user__respostausuario', filter=Q(user__respostausuario__foi_correta=True))
        ).filter(total_respostas__gt=0)
        
        ordenacao = ('-total_acertos', '-streak_data__current_streak')
        
        queryset_ranqueado = base_queryset.annotate(
            rank=Window(
                expression=Rank(),
                order_by=[F(field[1:]).desc() if field.startswith('-') else F(field).asc() for field in ordenacao]
            )
        ).order_by(*ordenacao)

        # Filtro correto para UserProfile
        posicao_usuario_logado = queryset_ranqueado.filter(user=request.user).first()

    # =======================================================================
    # LÓGICA PARA BUSCAR RECOMPENSAS EM DISPUTA (sem alterações)
    # =======================================================================
    recompensas_em_disputa = []
    gatilho_recompensa = None
    if periodo == 'semanal':
        gatilho_recompensa = RegraRecompensa.Gatilho.RANKING_SEMANAL_TOP_N
    elif periodo == 'mensal':
        gatilho_recompensa = RegraRecompensa.Gatilho.RANKING_MENSAL_TOP_N

    if gatilho_recompensa:
        regras_ativas = RegraRecompensa.objects.filter(
            ativo=True, 
            gatilho=gatilho_recompensa
        ).prefetch_related('avatares', 'bordas', 'banners')
        
        avatares = list(chain.from_iterable(regra.avatares.all() for regra in regras_ativas))
        bordas = list(chain.from_iterable(regra.bordas.all() for regra in regras_ativas))
        banners = list(chain.from_iterable(regra.banners.all() for regra in regras_ativas))
        
        recompensas_em_disputa = sorted(list(set(avatares + bordas + banners)), key=lambda x: x.nome)

    # =======================================================================
    # FINALIZAÇÃO E CONTEXTO (sem alterações)
    # =======================================================================
    
    page_obj, page_numbers, per_page = paginar_itens(request, queryset_ranqueado, 25)

    context = {
        'ranking_list': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'posicao_usuario_logado': posicao_usuario_logado,
        'recompensas_em_disputa': recompensas_em_disputa,
        'periodo_ativo': periodo,
        'titulo_ranking': titulo_ranking,
    }
    
    return render(request, 'gamificacao/ranking.html', context)