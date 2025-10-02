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
from django.db.models import Max

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
from django.db.models.functions import Rank, DenseRank
from django.urls import reverse
@login_required
def ranking(request):
    """
    Exibe a página de ranking, com lógica aprimorada para exibir prêmios por faixa,
    incluindo XP e Moedas, e uma mensagem de parabéns para os vencedores.
    
    MELHORIAS IMPLEMENTADAS:
    - Usa DenseRank para evitar saltos na classificação em caso de empates.
    - Exibe apenas o TOP 10 e, separadamente, a posição do usuário logado se ele estiver fora do TOP 10.
    - Critérios de desempate foram aprimorados e clarificados.
    - Carrega avatares e bordas dos usuários para uma UI mais rica.
    - Adiciona um "Pódio Anterior" para os rankings semanais e mensais.
    """
    verificar_e_gerar_rankings()

    periodo = request.GET.get('periodo', 'geral')
    queryset_ranqueado = UserProfile.objects.none()
    titulo_ranking = "Ranking Geral"
    
    vencedores_semana_anterior = None
    vencedores_mes_anterior = None

    if periodo == 'semanal':
        titulo_ranking = "Ranking Semanal"
        ultima_semana = RankingSemanal.objects.order_by('-ano', '-semana').values('ano', 'semana').first()
        if ultima_semana:
            queryset_ranqueado = RankingSemanal.objects.filter(
                ano=ultima_semana['ano'], semana=ultima_semana['semana']
            ).select_related(
                'user_profile__user', 'user_profile__streak_data', 
                'user_profile__avatar_equipado', 'user_profile__borda_equipada'
            ).annotate(
                rank=F('posicao'), nome=F('user_profile__nome'), sobrenome=F('user_profile__sobrenome'), 
                total_acertos=F('acertos_periodo'), total_respostas=F('respostas_periodo'), 
            ).order_by('posicao', '-user_profile__streak_data__current_streak')
            
            # Busca vencedores da semana anterior
            data_ref = date.fromisocalendar(ultima_semana['ano'], ultima_semana['semana'], 1) - timedelta(days=7)
            ano_anterior, semana_anterior, _ = data_ref.isocalendar()
            vencedores_semana_anterior = RankingSemanal.objects.filter(
                ano=ano_anterior, semana=semana_anterior, posicao__lte=2
            ).select_related('user_profile__user', 'user_profile__avatar_equipado', 'user_profile__borda_equipada').order_by('posicao')

    elif periodo == 'mensal':
        titulo_ranking = "Ranking Mensal"
        ultimo_mes = RankingMensal.objects.order_by('-ano', '-mes').values('ano', 'mes').first()
        if ultimo_mes:
            queryset_ranqueado = RankingMensal.objects.filter(
                ano=ultimo_mes['ano'], mes=ultimo_mes['mes']
            ).select_related(
                'user_profile__user', 'user_profile__streak_data',
                'user_profile__avatar_equipado', 'user_profile__borda_equipada'
            ).annotate(
                rank=F('posicao'), nome=F('user_profile__nome'), sobrenome=F('user_profile__sobrenome'), 
                total_acertos=F('acertos_periodo'), total_respostas=F('respostas_periodo'), 
            ).order_by('posicao', '-user_profile__streak_data__current_streak')

            # Busca vencedores do mês anterior
            data_ref = date(ultimo_mes['ano'], ultimo_mes['mes'], 1) - timedelta(days=1)
            vencedores_mes_anterior = RankingMensal.objects.filter(
                ano=data_ref.year, mes=data_ref.month, posicao__lte=2
            ).select_related('user_profile__user', 'user_profile__avatar_equipado', 'user_profile__borda_equipada').order_by('posicao')
            
    else: # Período 'geral'
        base_queryset = UserProfile.objects.filter(user__is_active=True, user__is_staff=False, user__respostausuario__isnull=False).select_related(
            'user', 'streak_data', 'avatar_equipado', 'borda_equipada'
        ).annotate(
            total_respostas_geral=Count('user__respostausuario'), 
            total_acertos_geral=Count('user__respostausuario', filter=Q(user__respostausuario__foi_correta=True))
        ).distinct()
        
        ordenacao = ('-total_acertos_geral', '-streak_data__current_streak', '-total_respostas_geral')
        
        queryset_ranqueado = base_queryset.annotate(
            rank=Window(expression=DenseRank(), order_by=[F(field[1:]).desc() if field.startswith('-') else F(field).asc() for field in ordenacao])
        ).order_by(*ordenacao)

    # --- LÓGICA ROBUSTA PARA ENCONTRAR O USUÁRIO E MONTAR A LISTA DE EXIBIÇÃO ---
    full_ranking_list = list(queryset_ranqueado)
    posicao_usuario_logado = None

    for item in full_ranking_list:
        user_id_item = item.user.id if periodo == 'geral' else item.user_profile.user.id
        if user_id_item == request.user.id:
            posicao_usuario_logado = item
            break

    ranking_top_10 = full_ranking_list[:10]
    usuario_no_top_10 = False
    if posicao_usuario_logado:
        for item_top_10 in ranking_top_10:
            user_id_item = item_top_10.user.id if periodo == 'geral' else item_top_10.user_profile.user.id
            if user_id_item == request.user.id:
                usuario_no_top_10 = True
                break
    
    ranking_para_exibir = ranking_top_10
    if posicao_usuario_logado and not usuario_no_top_10:
        setattr(posicao_usuario_logado, 'is_user_outside_top_10', True)
        ranking_para_exibir.append(posicao_usuario_logado)
    
    # --- LÓGICA DE PRÊMIOS (sem alterações) ---
    premios_por_faixa = []
    gatilho_campanha = None
    agora = timezone.now()

    if periodo == 'semanal':
        gatilho_campanha = Campanha.Gatilho.RANKING_SEMANAL_CONCLUIDO
    elif periodo == 'mensal':
        gatilho_campanha = Campanha.Gatilho.RANKING_MENSAL_CONCLUIDO

    if gatilho_campanha:
        campanhas_ativas = Campanha.objects.filter(ativo=True, gatilho=gatilho_campanha, data_inicio__lte=agora).filter(Q(data_fim__gte=agora) | Q(data_fim__isnull=True))
        all_reward_ids = {'avatares': set(), 'bordas': set(), 'banners': set()}
        for campanha in campanhas_ativas:
            for grupo in campanha.grupos_de_condicoes:
                all_reward_ids['avatares'].update(grupo.get('avatares', [])); all_reward_ids['bordas'].update(grupo.get('bordas', [])); all_reward_ids['banners'].update(grupo.get('banners', []))
        avatares = {a.id: a for a in Avatar.objects.filter(id__in=all_reward_ids['avatares'])}; bordas = {b.id: b for b in Borda.objects.filter(id__in=all_reward_ids['bordas'])}; banners = {b.id: b for b in Banner.objects.filter(id__in=all_reward_ids['banners'])}
        faixas_processadas = {}
        for campanha in campanhas_ativas:
            for grupo in campanha.grupos_de_condicoes:
                descricao_faixa = ""; pos_exata = grupo.get('condicao_posicao_exata'); pos_ate = grupo.get('condicao_posicao_ate')
                if pos_exata: descricao_faixa = f"Para o {pos_exata}º Lugar"
                elif pos_ate: descricao_faixa = "Para o 1º Lugar" if pos_ate == 1 else f"Prêmios do 1º ao {pos_ate}º Lugar"
                if not descricao_faixa: continue
                if descricao_faixa not in faixas_processadas: faixas_processadas[descricao_faixa] = {'recompensas': set(), 'xp': 0, 'moedas': 0}
                faixas_processadas[descricao_faixa]['xp'] += grupo.get('xp_extra', 0); faixas_processadas[descricao_faixa]['moedas'] += grupo.get('moedas_extras', 0)
                recompensas_grupo = []; recompensas_grupo.extend([avatares[id] for id in grupo.get('avatares', []) if id in avatares]); recompensas_grupo.extend([bordas[id] for id in grupo.get('bordas', []) if id in bordas]); recompensas_grupo.extend([banners[id] for id in grupo.get('banners', []) if id in banners]); faixas_processadas[descricao_faixa]['recompensas'].update(recompensas_grupo)
        premios_por_faixa = sorted([{'faixa': faixa, 'recompensas': list(dados['recompensas']), 'xp': dados['xp'], 'moedas': dados['moedas']} for faixa, dados in faixas_processadas.items()], key=lambda x: int(''.join(filter(str.isdigit, x['faixa']))))
    
    mensagem_vencedor = None
    if periodo != 'geral' and request.user.userprofile:
        tem_premios_pendentes = RecompensaPendente.objects.filter(user_profile=request.user.userprofile, resgatado_em__isnull=True, origem_desbloqueio__icontains='campanha').filter(Q(origem_desbloqueio__icontains='semanal') | Q(origem_desbloqueio__icontains='mensal')).exists()
        if tem_premios_pendentes:
            mensagem_vencedor = {'titulo': 'Parabéns, Campeão!', 'texto': 'Você ganhou prêmios no último período do ranking! Eles já foram enviados para sua Caixa de Recompensas para serem resgatados.', 'link_caixa': reverse('caixa_de_recompensas')}

    context = {
        'ranking_list': ranking_para_exibir,
        'posicao_usuario_logado': posicao_usuario_logado,
        'premios_por_faixa': premios_por_faixa,
        'mensagem_vencedor': mensagem_vencedor,
        'periodo_ativo': periodo,
        'titulo_ranking': titulo_ranking,
        'vencedores_semana_anterior': vencedores_semana_anterior,
        'vencedores_mes_anterior': vencedores_mes_anterior,
    }
    return render(request, 'gamificacao/ranking.html', context)

@login_required
def loja(request):
    """
    Exibe a Loja de Recompensas com filtros, ordenação e paginação,
    agora com lógica para exibir itens que o usuário pode comprar e itens
    que estão bloqueados por requisito de nível.
    """
    user_profile = request.user.userprofile
    
    avatares_base = Avatar.objects.filter(tipos_desbloqueio__nome='LOJA', preco_moedas__gt=0).prefetch_related('tipos_desbloqueio')
    bordas_base = Borda.objects.filter(tipos_desbloqueio__nome='LOJA', preco_moedas__gt=0).prefetch_related('tipos_desbloqueio')
    banners_base = Banner.objects.filter(tipos_desbloqueio__nome='LOJA', preco_moedas__gt=0).prefetch_related('tipos_desbloqueio')

    all_items_base = list(chain(avatares_base, bordas_base, banners_base))

    itens_visiveis = []
    nivel_atual = user_profile.gamificacao_data.level
    
    avatares_possuidos = set(user_profile.avatares_desbloqueados.values_list('avatar_id', flat=True))
    bordas_possuidas = set(user_profile.bordas_desbloqueadas.values_list('borda_id', flat=True))
    banners_possuidas = set(user_profile.banners_desbloqueados.values_list('banner_id', flat=True))

    for item in all_items_base:
        item.ja_possui = False
        item.is_locked = False
        item.unlock_condition = ''
        
        item_type_name = item.__class__.__name__
        if item_type_name == 'Avatar' and item.id in avatares_possuidos:
            item.ja_possui = True
        elif item_type_name == 'Borda' and item.id in bordas_possuidas:
            item.ja_possui = True
        elif item_type_name == 'Banner' and item.id in banners_possuidas:
            item.ja_possui = True
        
        if not item.ja_possui:
            tipos_desbloqueio_nomes = {t.nome for t in item.tipos_desbloqueio.all()}
            if 'NIVEL' in tipos_desbloqueio_nomes:
                if nivel_atual < item.nivel_necessario:
                    item.is_locked = True
                    item.unlock_condition = f"Requer Nível {item.nivel_necessario}"

        itens_visiveis.append(item)

    filtro_tipo = request.GET.get('tipo', '')
    filtro_raridade = request.GET.get('raridade', '')

    filtered_items = itens_visiveis
    if filtro_tipo:
        filtered_items = [item for item in filtered_items if item.__class__.__name__ == filtro_tipo]
    if filtro_raridade:
        filtered_items = [item for item in filtered_items if item.raridade == filtro_raridade]

    # =======================================================================
    # INÍCIO DA CORREÇÃO: Lógica para ordenar por possuídos primeiro
    # =======================================================================
    sort_by = request.GET.get('sort_by', 'preco_asc')
    sort_options = {
        'preco_asc': ('Preço (Menor > Maior)', lambda item: (item.ja_possui, item.is_locked, item.preco_moedas)),
        'preco_desc': ('Preço (Maior > Menor)', lambda item: (item.ja_possui, item.is_locked, -item.preco_moedas)),
        'nome_asc': ('Nome (A-Z)', lambda item: (item.ja_possui, item.is_locked, item.nome)),
    }
    
    # A ordenação por `item.ja_possui` (False vem antes de True) já coloca os não possuídos primeiro.
    # O pedido é o contrário: possuídos primeiro. Então, invertemos a lógica.
    sort_key_lambda = sort_options.get(sort_by, sort_options['preco_asc'])[1]
    
    # Nova chave que prioriza `not item.ja_possui`.
    # Itens possuídos (ja_possui=True) terão a chave (False, ...), vindo primeiro.
    # Itens não possuídos (ja_possui=False) terão a chave (True, ...), vindo depois.
    final_sort_key = lambda item: (
        not item.ja_possui,  # Critério primário: possuídos primeiro
        sort_key_lambda(item)[1], # Critério secundário: bloqueado por nível
        sort_key_lambda(item)[2]  # Critério terciário: ordenação do usuário
    )
    
    sorted_items = sorted(filtered_items, key=final_sort_key)
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================
    
    page_obj, page_numbers, per_page = paginar_itens(request, sorted_items, items_per_page=8)

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
        
        # =======================================================================
        # INÍCIO DA CORREÇÃO: Torna a verificação do tipo de item case-insensitive
        # =======================================================================
        Model = None
        if item_tipo and isinstance(item_tipo, str):
            # Capitaliza a string ("avatar" -> "Avatar") para corresponder à chave do ModelMap
            Model = ModelMap.get(item_tipo.capitalize())
        # =======================================================================
        # FIM DA CORREÇÃO
        # =======================================================================

        if not Model:
            return JsonResponse({'status': 'error', 'message': 'Tipo de item inválido.'}, status=400)
        
        item = get_object_or_404(Model, id=item_id, tipos_desbloqueio__nome='LOJA')
        
        user_profile = request.user.userprofile
        gamificacao_data = user_profile.gamificacao_data

        if gamificacao_data.moedas < item.preco_moedas:
            return JsonResponse({'status': 'error', 'message': 'Você não tem moedas suficientes.'}, status=403)

        created = False
        if item_tipo.capitalize() == 'Avatar':
            _, created = AvatarUsuario.objects.get_or_create(user_profile=user_profile, avatar=item)
        elif item_tipo.capitalize() == 'Borda':
            _, created = BordaUsuario.objects.get_or_create(user_profile=user_profile, borda=item)
        elif item_tipo.capitalize() == 'Banner':
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
        user_profile = request.user.userprofile

        # =======================================================================
        # ✅ INÍCIO DA ALTERAÇÃO: Lógica de verificação robusta
        # =======================================================================
        try:
            # 1. Tenta encontrar a recompensa pendente pelo ID e usuário.
            recompensa_pendente = RecompensaPendente.objects.get(
                id=pendente_id,
                user_profile=user_profile
            )
        except RecompensaPendente.DoesNotExist:
            # Se não encontrar, retorna 404.
            return JsonResponse({'status': 'error', 'message': 'Recompensa não encontrada.'}, status=404)

        # 2. Verifica se a recompensa JÁ foi resgatada.
        if recompensa_pendente.resgatado_em is not None:
            # Se já foi, retorna um erro específico (409 Conflict)
            return JsonResponse({
                'status': 'already_redeemed', 
                'message': 'Este tesouro já foi revelado! Por favor, atualize a página para ver sua coleção atualizada.'
            }, status=409) # 409 Conflict é o status HTTP ideal para esta situação.
        
        # 3. Garante que a recompensa ainda existe antes de tentar resgatar
        if not recompensa_pendente.recompensa:
            recompensa_pendente.delete() # Limpa o item pendente quebrado
            return JsonResponse({'status': 'error', 'message': 'Este item não existe mais e foi removido da sua caixa.'}, status=404)

        # 4. Procede com o resgate se tudo estiver OK.
        sucesso = recompensa_pendente.resgatar()
        # =======================================================================
        # FIM DA ALTERAÇÃO
        # =======================================================================

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