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
    AvatarUsuario, BordaUsuario, BannerUsuario, RecompensaUsuario, 
    VariavelDoJogo 
)


# gamificacao/views.py

# gamificacao/views.py

@login_required
def ranking(request):
    """
    Exibe a página de ranking, com lógica aprimorada para exibir prêmios por faixa,
    incluindo XP e Moedas, e uma mensagem de parabéns para os vencedores.
    """
    verificar_e_gerar_rankings()

    periodo = request.GET.get('periodo', 'geral')
    queryset_ranqueado = UserProfile.objects.none()
    posicao_usuario_logado = None
    titulo_ranking = "Ranking Geral"
    
    # --- LÓGICA DE BUSCA DO RANKING (sem alterações) ---
    if periodo == 'semanal':
        titulo_ranking = "Ranking Semanal"
        ultima_semana = RankingSemanal.objects.order_by('-ano', '-semana').values('ano', 'semana').first()
        if ultima_semana:
            queryset_ranqueado = RankingSemanal.objects.filter(ano=ultima_semana['ano'], semana=ultima_semana['semana']).select_related('user_profile__user', 'user_profile__streak_data').annotate(rank=F('posicao'), nome=F('user_profile__nome'), sobrenome=F('user_profile__sobrenome'), user=F('user_profile__user'), total_acertos=F('acertos_periodo'), total_respostas=F('respostas_periodo'), streak_data=F('user_profile__streak_data')).order_by('posicao')
            
    elif periodo == 'mensal':
        titulo_ranking = "Ranking Mensal"
        ultimo_mes = RankingMensal.objects.order_by('-ano', '-mes').values('ano', 'mes').first()
        if ultimo_mes:
            queryset_ranqueado = RankingMensal.objects.filter(ano=ultimo_mes['ano'], mes=ultimo_mes['mes']).select_related('user_profile__user', 'user_profile__streak_data').annotate(rank=F('posicao'), nome=F('user_profile__nome'), sobrenome=F('user_profile__sobrenome'), user=F('user_profile__user'), total_acertos=F('acertos_periodo'), total_respostas=F('respostas_periodo'), streak_data=F('user_profile__streak_data')).order_by('posicao')

    else: # Período 'geral'
        base_queryset = UserProfile.objects.filter(user__is_active=True, user__is_staff=False).select_related('user', 'streak_data').annotate(total_respostas_geral=Count('user__respostausuario'), total_acertos_geral=Count('user__respostausuario', filter=Q(user__respostausuario__foi_correta=True))).filter(total_respostas_geral__gt=0)
        ordenacao = ('-total_acertos_geral', '-streak_data__current_streak')
        queryset_ranqueado = base_queryset.annotate(rank=Window(expression=Rank(), order_by=[F(field[1:]).desc() if field.startswith('-') else F(field).asc() for field in ordenacao])).order_by(*ordenacao)

    if queryset_ranqueado.exists():
        if periodo != 'geral':
             posicao_usuario_logado = queryset_ranqueado.filter(user_profile__user=request.user).first()
        else:
             posicao_usuario_logado = queryset_ranqueado.filter(user=request.user).first()

    premios_por_faixa = []
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
        
        all_reward_ids = {'avatares': set(), 'bordas': set(), 'banners': set()}
        for campanha in campanhas_ativas:
            for grupo in campanha.grupos_de_condicoes:
                all_reward_ids['avatares'].update(grupo.get('avatares', []))
                all_reward_ids['bordas'].update(grupo.get('bordas', []))
                all_reward_ids['banners'].update(grupo.get('banners', []))

        avatares = {a.id: a for a in Avatar.objects.filter(id__in=all_reward_ids['avatares'])}
        bordas = {b.id: b for b in Borda.objects.filter(id__in=all_reward_ids['bordas'])}
        banners = {b.id: b for b in Banner.objects.filter(id__in=all_reward_ids['banners'])}
        
        faixas_processadas = {}
        for campanha in campanhas_ativas:
            for grupo in campanha.grupos_de_condicoes:
                descricao_faixa = ""
                pos_exata = grupo.get('condicao_posicao_exata')
                pos_ate = grupo.get('condicao_posicao_ate')
                
                # =======================================================================
                # INÍCIO DA CORREÇÃO DA MENSAGEM
                # =======================================================================
                if pos_exata:
                    descricao_faixa = f"Para o {pos_exata}º Lugar"
                elif pos_ate:
                    if pos_ate == 1:
                        descricao_faixa = "Para o 1º Lugar"
                    else:
                        descricao_faixa = f"Prêmios do 1º ao {pos_ate}º Lugar"
                # =======================================================================
                # FIM DA CORREÇÃO DA MENSAGEM
                # =======================================================================
                
                if not descricao_faixa: continue
                
                if descricao_faixa not in faixas_processadas:
                    faixas_processadas[descricao_faixa] = {'recompensas': set(), 'xp': 0, 'moedas': 0}

                faixas_processadas[descricao_faixa]['xp'] += grupo.get('xp_extra', 0)
                faixas_processadas[descricao_faixa]['moedas'] += grupo.get('moedas_extras', 0)
                
                recompensas_grupo = []
                recompensas_grupo.extend([avatares[id] for id in grupo.get('avatares', []) if id in avatares])
                recompensas_grupo.extend([bordas[id] for id in grupo.get('bordas', []) if id in bordas])
                recompensas_grupo.extend([banners[id] for id in grupo.get('banners', []) if id in banners])
                faixas_processadas[descricao_faixa]['recompensas'].update(recompensas_grupo)
        
        premios_por_faixa = sorted(
            [{'faixa': faixa, 'recompensas': list(dados['recompensas']), 'xp': dados['xp'], 'moedas': dados['moedas']} for faixa, dados in faixas_processadas.items()],
            key=lambda x: int(''.join(filter(str.isdigit, x['faixa'])))
        )
    
    mensagem_vencedor = None
    if periodo != 'geral':
        tem_premios_pendentes = RecompensaPendente.objects.filter(
            user_profile=request.user.userprofile,
            resgatado_em__isnull=True,
            origem_desbloqueio__icontains='campanha'
        ).filter(
            Q(origem_desbloqueio__icontains='semanal') | Q(origem_desbloqueio__icontains='mensal')
        ).exists()

        if tem_premios_pendentes:
            mensagem_vencedor = {
                'titulo': 'Parabéns, Campeão!',
                'texto': 'Você ganhou prêmios no último período do ranking! Eles já foram enviados para sua Caixa de Recompensas para serem resgatados.',
                'link_caixa': reverse('caixa_de_recompensas')
            }
            
    page_obj, page_numbers, per_page = paginar_itens(request, queryset_ranqueado, 25)

    context = {
        'ranking_list': page_obj, 'paginated_object': page_obj, 'page_numbers': page_numbers,
        'per_page': per_page, 'posicao_usuario_logado': posicao_usuario_logado,
        'premios_por_faixa': premios_por_faixa,
        'mensagem_vencedor': mensagem_vencedor,
        'periodo_ativo': periodo,
        'titulo_ranking': titulo_ranking,
    }
    return render(request, 'gamificacao/ranking.html', context)


@login_required
def loja(request):
    """
    Exibe a Loja de Recompensas com filtros, ordenação e paginação.
    """
    user_profile = request.user.userprofile
    
    avatares = Avatar.objects.filter(tipos_desbloqueio__nome='LOJA', preco_moedas__gt=0)
    bordas = Borda.objects.filter(tipos_desbloqueio__nome='LOJA', preco_moedas__gt=0)
    banners = Banner.objects.filter(tipos_desbloqueio__nome='LOJA', preco_moedas__gt=0)
    
    all_items_qs = list(chain(avatares, bordas, banners))

    # --- LÓGICA DE FILTRAGEM ---
    filtro_tipo = request.GET.get('tipo', '')
    filtro_raridade = request.GET.get('raridade', '')

    filtered_items = all_items_qs
    if filtro_tipo:
        filtered_items = [item for item in filtered_items if item.__class__.__name__ == filtro_tipo]
    if filtro_raridade:
        filtered_items = [item for item in filtered_items if item.raridade == filtro_raridade]

    # --- LÓGICA DE ORDENAÇÃO ---
    sort_by = request.GET.get('sort_by', 'preco_asc')
    sort_options = {
        'preco_asc': ('Preço (Menor > Maior)', lambda item: item.preco_moedas),
        'preco_desc': ('Preço (Maior > Menor)', lambda item: -item.preco_moedas),
        'nome_asc': ('Nome (A-Z)', lambda item: item.nome),
    }
    
    sort_key = sort_options.get(sort_by, sort_options['preco_asc'])[1]
    sorted_items = sorted(filtered_items, key=sort_key)

    # --- LÓGICA DE VERIFICAÇÃO DE POSSE ---
    avatares_possuidos = set(user_profile.avatares_desbloqueados.values_list('avatar_id', flat=True))
    bordas_possuidas = set(user_profile.bordas_desbloqueadas.values_list('borda_id', flat=True))
    banners_possuidos = set(user_profile.banners_desbloqueados.values_list('banner_id', flat=True))

    for item in sorted_items:
        item_type_name = item.__class__.__name__
        if item_type_name == 'Avatar' and item.id in avatares_possuidos:
            item.ja_possui = True
        elif item_type_name == 'Borda' and item.id in bordas_possuidas:
            item.ja_possui = True
        elif item_type_name == 'Banner' and item.id in banners_possuidos:
            item.ja_possui = True
        else:
            item.ja_possui = False

    # --- LÓGICA DE PAGINAÇÃO ---
    page_obj, page_numbers, per_page = paginar_itens(request, sorted_items, items_per_page=20)

    context = {
        'itens_loja': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'saldo_atual': user_profile.gamificacao_data.moedas,
        'raridade_choices': Avatar.Raridade.choices,
        'tipo_choices': [('Avatar', 'Avatares'), ('Borda', 'Bordas'), ('Banner', 'Banners')],
        'sort_options': {key: val[0] for key, val in sort_options.items()},
        'active_filters': request.GET,
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
        
        # =======================================================================
        # CORREÇÃO DA QUERY AQUI
        # Trocamos `tipo_desbloqueio='LOJA'` por `tipos_desbloqueio__nome='LOJA'`
        # =======================================================================
        item = get_object_or_404(Model, id=item_id, tipos_desbloqueio__nome='LOJA')
        # =======================================================================
        
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
    

# gamificacao/views.py

# gamificacao/views.py

@login_required
def campanhas_ativas(request):
    """
    Exibe uma página para os usuários com todas as campanhas e eventos ativos,
    agora com detalhes completos e legíveis sobre TODAS as condições.
    """
    agora = timezone.now()
    campanhas = Campanha.objects.filter(
        ativo=True,
        data_inicio__lte=agora
    ).filter(
        Q(data_fim__gte=agora) | Q(data_fim__isnull=True)
    ).prefetch_related('simulado_especifico').order_by('data_fim')

    all_reward_ids = {'avatares': set(), 'bordas': set(), 'banners': set()}
    all_variavel_ids = set()
    for campanha in campanhas:
        for grupo in campanha.grupos_de_condicoes:
            all_reward_ids['avatares'].update(grupo.get('avatares', []))
            all_reward_ids['bordas'].update(grupo.get('bordas', []))
            all_reward_ids['banners'].update(grupo.get('banners', []))
            if 'condicoes' in grupo:
                for cond in grupo['condicoes']:
                    all_variavel_ids.add(cond.get('variavel_id'))

    avatars_map = {a.id: a for a in Avatar.objects.filter(id__in=all_reward_ids['avatares'])}
    bordas_map = {b.id: b for b in Borda.objects.filter(id__in=all_reward_ids['bordas'])}
    banners_map = {b.id: b for b in Banner.objects.filter(id__in=all_reward_ids['banners'])}
    variaveis_map = {v.id: v for v in VariavelDoJogo.objects.filter(id__in=all_variavel_ids)}

    for campanha in campanhas:
        for grupo in campanha.grupos_de_condicoes:
            grupo['recompensas_detalhadas'] = []
            grupo['recompensas_detalhadas'].extend([avatars_map[id] for id in grupo.get('avatares', []) if id in avatars_map])
            grupo['recompensas_detalhadas'].extend([bordas_map[id] for id in grupo.get('bordas', []) if id in bordas_map])
            grupo['recompensas_detalhadas'].extend([banners_map[id] for id in grupo.get('banners', []) if id in banners_map])
            
            # =======================================================================
            # INÍCIO DA ALTERAÇÃO: Lógica unificada para exibir todas as condições
            # =======================================================================
            grupo['condicoes_humanizadas'] = []
            
            # 1. Processa as condições específicas do gatilho (as "antigas")
            pos_exata = grupo.get('condicao_posicao_exata')
            pos_ate = grupo.get('condicao_posicao_ate')
            min_acertos = grupo.get('condicao_min_acertos_percent')

            if pos_exata:
                grupo['condicoes_humanizadas'].append(f"Alcançar a <strong>{pos_exata}ª posição</strong> no ranking.")
            if pos_ate:
                grupo['condicoes_humanizadas'].append(f"Ficar entre os <strong>{pos_ate} primeiros</strong> no ranking.")
            if min_acertos:
                grupo['condicoes_humanizadas'].append(f"Atingir no mínimo <strong>{min_acertos}% de acertos</strong>.")

            # 2. Processa as condições gerais baseadas em Variáveis de Jogo
            if 'condicoes' in grupo:
                for cond in grupo['condicoes']:
                    variavel = variaveis_map.get(cond['variavel_id'])
                    if variavel:
                        grupo['condicoes_humanizadas'].append(f"Ter <strong>{variavel.nome_exibicao}</strong> {cond['operador']} {cond['valor']}")
            
            # 3. Adiciona uma mensagem padrão se nenhuma condição for encontrada
            if not grupo['condicoes_humanizadas']:
                 grupo['condicoes_humanizadas'].append("Recompensa concedida por participar do evento.")
            # =======================================================================
            # FIM DA ALTERAÇÃO
            # =======================================================================

    context = {
        'campanhas_ativas': campanhas,
        'titulo_pagina': 'Eventos e Campanhas',
        'active_tab': 'campanhas_ativas',
    }
    return render(request, 'gamificacao/campanhas_ativas.html', context)