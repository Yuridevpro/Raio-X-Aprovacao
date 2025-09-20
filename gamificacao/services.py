# gamificacao/services.py (ARQUIVO COMPLETO)

from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.contenttypes.models import ContentType
from gestao.utils import criar_log
from gestao.models import LogAtividade
from .models import RegraRecompensa, RecompensaUsuario

# Imports dos modelos
from pratica.models import RespostaUsuario
from usuarios.models import UserProfile
from .models import (
    Conquista, ConquistaUsuario, ProfileGamificacao, MetaDiariaUsuario,
    RankingSemanal, RankingMensal, TarefaAgendadaLog,
    Avatar, Borda, Banner,
    AvatarUsuario, BordaUsuario, BannerUsuario,
    GamificationSettings
)
from simulados.models import Simulado
from simulados.models import SessaoSimulado
from django.utils.dateparse import parse_datetime


def calcular_xp_para_nivel(level):
    """Calcula o total de XP necessário para atingir um determinado nível."""
    return 50 * (level ** 2) + 50 * level

def processar_resposta_gamificacao(user, questao, alternativa_selecionada):
    """
    Motor de regras de gamificação. Verifica as regras ANTES de salvar a resposta.
    """
    settings = GamificationSettings.load()
    user_profile, _ = UserProfile.objects.get_or_create(user=user)
    gamificacao_data, _ = ProfileGamificacao.objects.get_or_create(user_profile=user_profile)
    hoje = date.today()
    meta_hoje, _ = MetaDiariaUsuario.objects.get_or_create(user_profile=user_profile, data=hoje)

    correta = (alternativa_selecionada == questao.gabarito)

    try:
        ultima_resposta_geral = RespostaUsuario.objects.filter(usuario=user).latest('data_resposta')
        min_tempo = timedelta(seconds=settings.tempo_minimo_entre_respostas_segundos)
        if timezone.now() - ultima_resposta_geral.data_resposta < min_tempo:
            return {"xp_ganho": 0, "bonus_ativo": False, "level_up_info": None, "nova_conquista": None, "meta_completa_info": None, "correta": correta, "gabarito": questao.gabarito}
    except RespostaUsuario.DoesNotExist:
        pass

    resposta_anterior = RespostaUsuario.objects.filter(usuario=user, questao=questao).first()
    
    if resposta_anterior:
        cooldown = timedelta(hours=settings.cooldown_mesma_questao_horas)
        if timezone.now() - resposta_anterior.data_resposta < cooldown:
            return {"xp_ganho": 0, "bonus_ativo": False, "level_up_info": None, "nova_conquista": None, "meta_completa_info": None, "correta": correta, "gabarito": questao.gabarito}

    if settings.habilitar_teto_xp_diario and meta_hoje.xp_ganho_dia >= settings.teto_xp_diario:
        return {"xp_ganho": 0, "bonus_ativo": False, "level_up_info": None, "nova_conquista": None, "meta_completa_info": None, "correta": correta, "gabarito": questao.gabarito}

    RespostaUsuario.objects.update_or_create(
        usuario=user, questao=questao,
        defaults={'alternativa_selecionada': alternativa_selecionada, 'foi_correta': correta}
    )
    
    xp_base = 0
    if correta:
        if not resposta_anterior:
            xp_base = settings.xp_acerto_primeira_vez
        elif not resposta_anterior.foi_correta:
            xp_base = settings.xp_acerto_redencao
        else:
            xp_base = settings.xp_por_acerto
    else:
        xp_base = settings.xp_por_erro

    if correta:
        gamificacao_data.acertos_consecutivos += 1
        if gamificacao_data.acertos_consecutivos >= settings.acertos_consecutivos_para_bonus:
            gamificacao_data.bonus_xp_ativo = True
    else:
        gamificacao_data.acertos_consecutivos = 0
        gamificacao_data.bonus_xp_ativo = False
    
    xp_ganho = xp_base
    bonus_aplicado = False
    if correta and gamificacao_data.bonus_xp_ativo:
        xp_ganho = int(xp_base * settings.bonus_multiplicador_acertos_consecutivos)
        bonus_aplicado = True

    gamificacao_data.xp += xp_ganho
    meta_completa_info = _processar_meta_diaria(user_profile, gamificacao_data, meta_hoje, xp_ganho, settings)
    level_up_info = _verificar_level_up(gamificacao_data)
    gamificacao_data.save()
    
    if level_up_info: _verificar_desbloqueio_recompensas(user_profile)
    
    nova_conquista = _verificar_e_registrar_conquistas(user_profile)
    if nova_conquista: _verificar_desbloqueio_recompensas(user_profile, conquista_ganha=nova_conquista)

    return {
        "xp_ganho": xp_ganho, "bonus_ativo": bonus_aplicado,
        "level_up_info": level_up_info, "nova_conquista": nova_conquista,
        "meta_completa_info": meta_completa_info, "correta": correta,
        "gabarito": questao.gabarito
    }

def _processar_meta_diaria(user_profile, gamificacao_data, meta_hoje, xp_atual, settings):
    from .models import MetaDiariaUsuario
    meta_hoje.xp_ganho_dia += xp_atual
    meta_hoje.questoes_resolvidas += 1
    
    meta_completa_info = None
    if not meta_hoje.meta_atingida and meta_hoje.questoes_resolvidas >= settings.meta_diaria_questoes:
        meta_hoje.meta_atingida = True
        gamificacao_data.xp += settings.xp_bonus_meta_diaria
        meta_completa_info = {
            "xp_bonus": settings.xp_bonus_meta_diaria,
            "total_questoes": settings.meta_diaria_questoes
        }

    meta_hoje.save()
    return meta_completa_info

def _verificar_level_up(gamificacao_data):
    novo_level_info = None
    xp_necessario = calcular_xp_para_nivel(gamificacao_data.level)
    
    while gamificacao_data.xp >= xp_necessario:
        gamificacao_data.level += 1
        novo_level_info = {"novo_level": gamificacao_data.level}
        xp_necessario = calcular_xp_para_nivel(gamificacao_data.level)
        
    return novo_level_info

def _verificar_desbloqueio_recompensas(user_profile, conquista_ganha=None):
    from .models import Avatar, Borda, Banner, AvatarUsuario, BordaUsuario, BannerUsuario
    nivel_atual = user_profile.gamificacao_data.level
    
    avatares_por_nivel = Avatar.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual)
    for avatar in avatares_por_nivel:
        AvatarUsuario.objects.get_or_create(user_profile=user_profile, avatar=avatar)
        
    bordas_por_nivel = Borda.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual)
    for borda in bordas_por_nivel:
        BordaUsuario.objects.get_or_create(user_profile=user_profile, borda=borda)
        
    banners_por_nivel = Banner.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual)
    for banner in banners_por_nivel:
        BannerUsuario.objects.get_or_create(user_profile=user_profile, banner=banner)

    if conquista_ganha:
        avatares_por_conquista = Avatar.objects.filter(tipo_desbloqueio='CONQUISTA', conquista_necessaria=conquista_ganha)
        for avatar in avatares_por_conquista:
            AvatarUsuario.objects.get_or_create(user_profile=user_profile, avatar=avatar)
            
        bordas_por_conquista = Borda.objects.filter(tipo_desbloqueio='CONQUISTA', conquista_necessaria=conquista_ganha)
        for borda in bordas_por_conquista:
            BordaUsuario.objects.get_or_create(user_profile=user_profile, borda=borda)

        banners_por_conquista = Banner.objects.filter(tipo_desbloqueio='CONQUISTA', conquista_necessaria=conquista_ganha)
        for banner in banners_por_conquista:
            BannerUsuario.objects.get_or_create(user_profile=user_profile, banner=banner)

def _verificar_e_registrar_conquistas(user_profile):
    verificadores = [
        _verificar_conquistas_de_streak,
        _verificar_conquistas_de_volume,
        _verificar_conquistas_de_precisao,
    ]
    for funcao_verificadora in verificadores:
        nova_conquista = funcao_verificadora(user_profile)
        if nova_conquista:
            return nova_conquista
    return None

def _verificar_conquistas_de_streak(user_profile):
    current_streak = user_profile.streak_data.current_streak
    streaks_marcos = {'STREAK_3_DIAS': 3, 'STREAK_7_DIAS': 7, 'STREAK_30_DIAS': 30}
    
    for chave, dias in streaks_marcos.items():
        if current_streak >= dias:
            try:
                conquista = Conquista.objects.get(chave=chave)
                _, created = ConquistaUsuario.objects.get_or_create(user_profile=user_profile, conquista=conquista)
                if created: return conquista
            except Conquista.DoesNotExist: pass
    return None

def _verificar_conquistas_de_volume(user_profile):
    total_resolvidas = RespostaUsuario.objects.filter(usuario=user_profile.user).count()
    volume_marcos = {'PRIMEIRA_QUESTAO': 1, 'DEZ_QUESTOES': 10, 'CEM_QUESTOES': 100}

    for chave, quantidade in volume_marcos.items():
        if total_resolvidas >= quantidade:
            try:
                conquista = Conquista.objects.get(chave=chave)
                _, created = ConquistaUsuario.objects.get_or_create(user_profile=user_profile, conquista=conquista)
                if created: return conquista
            except Conquista.DoesNotExist: pass
    return None

def _verificar_conquistas_de_precisao(user_profile):
    acertos_seguidos = user_profile.gamificacao_data.acertos_consecutivos
    precisao_marcos = {'PRECISAO_10': 10}

    for chave, quantidade in precisao_marcos.items():
        if acertos_seguidos >= quantidade:
            try:
                conquista = Conquista.objects.get(chave=chave)
                _, created = ConquistaUsuario.objects.get_or_create(user_profile=user_profile, conquista=conquista)
                if created: return conquista
            except Conquista.DoesNotExist: pass
    return None

def verificar_e_gerar_rankings():
    _verificar_e_gerar_ranking_semanal()
    _verificar_e_gerar_ranking_mensal()

def _verificar_e_gerar_ranking_semanal():
    hoje = timezone.now()
    log_semanal, _ = TarefaAgendadaLog.objects.get_or_create(
        nome_tarefa='gerar_ranking_semanal',
        defaults={'ultima_execucao': hoje - timedelta(days=8)}
    )
    if (hoje - log_semanal.ultima_execucao).days < 7: return

    semana_passada_data = hoje.date() - timedelta(days=7)
    ano, semana, _ = semana_passada_data.isocalendar()
    
    start_of_week = date.fromisocalendar(ano, semana, 1)
    end_of_week = start_of_week + timedelta(days=6)
    
    sucesso = _processar_e_salvar_ranking('semanal', start_of_week, end_of_week)
    if sucesso:
        log_semanal.ultima_execucao = hoje
        log_semanal.save()

def _verificar_e_gerar_ranking_mensal():
    hoje = timezone.now()
    log_mensal, _ = TarefaAgendadaLog.objects.get_or_create(
        nome_tarefa='gerar_ranking_mensal',
        defaults={'ultima_execucao': hoje - timedelta(days=32)}
    )
    if log_mensal.ultima_execucao.month == hoje.month and log_mensal.ultima_execucao.year == hoje.year: return

    primeiro_dia_mes_atual = hoje.date().replace(day=1)
    ultimo_dia_mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
    primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)

    sucesso = _processar_e_salvar_ranking('mensal', primeiro_dia_mes_passado, ultimo_dia_mes_passado)
    if sucesso:
        log_mensal.ultima_execucao = hoje
        log_mensal.save()

def _processar_e_salvar_ranking(tipo, data_inicio, data_fim):
    respostas_no_periodo = RespostaUsuario.objects.filter(
        data_resposta__date__gte=data_inicio,
        data_resposta__date__lte=data_fim,
        usuario__is_staff=False,
        usuario__is_active=True
    )
    ranking_data = list(respostas_no_periodo
        .values('usuario_id')
        .annotate(acertos=Count('id', filter=Q(foi_correta=True)), respostas=Count('id'))
        .order_by('-acertos', '-respostas')
        .values('usuario_id', 'acertos', 'respostas')
    )
    if not ranking_data: return True

    user_profiles = UserProfile.objects.in_bulk([item['usuario_id'] for item in ranking_data])
    
    objetos_para_criar = []
    for i, item in enumerate(ranking_data):
        user_profile = user_profiles.get(item['usuario_id'])
        if not user_profile: continue

        if tipo == 'semanal':
            obj = RankingSemanal(
                user_profile=user_profile, ano=data_inicio.year, semana=data_inicio.isocalendar()[1],
                posicao=i + 1, acertos_periodo=item['acertos'], respostas_periodo=item['respostas']
            )
        else:
            obj = RankingMensal(
                user_profile=user_profile, ano=data_inicio.year, mes=data_inicio.month,
                posicao=i + 1, acertos_periodo=item['acertos'], respostas_periodo=item['respostas']
            )
        objetos_para_criar.append(obj)
    
    if objetos_para_criar:
        if tipo == 'semanal':
            RankingSemanal.objects.bulk_create(objetos_para_criar)
        else:
            RankingMensal.objects.bulk_create(objetos_para_criar)
            
    return True

def processar_conclusao_simulado(sessao):
    settings = GamificationSettings.load()
    user = sessao.usuario
    user_profile = user.userprofile
    gamificacao_data = user_profile.gamificacao_data
    simulado_id_str = str(sessao.simulado.id)

    cooldown_timestamp_str = gamificacao_data.cooldowns_ativos.get("simulados", {}).get(simulado_id_str)
    if cooldown_timestamp_str:
        cooldown_timestamp = parse_datetime(cooldown_timestamp_str)
        cooldown_delta = timedelta(hours=settings.cooldown_mesmo_simulado_horas)
        if timezone.now() < cooldown_timestamp + cooldown_delta:
            # CORREÇÃO: Retornar uma estrutura consistente mesmo em caso de cooldown
            return {'xp_ganho': 0, 'regras_info': [], 'level_up_info': None, 'novas_recompensas': [], 'percentual_acerto': 0}
    
    total_questoes = sessao.simulado.questoes.count()
    if total_questoes == 0: return {}

    total_acertos = sessao.respostas.filter(foi_correta=True).count()
    percentual_acerto = (total_acertos / total_questoes) * 100
    
    xp_ganho = 0
    if settings.usar_xp_dinamico_simulado:
        xp_bruto = 0
        xp_bruto += total_acertos * settings.xp_por_acerto
        if settings.xp_dinamico_considera_erros:
            total_erros = total_questoes - total_acertos
            xp_bruto += total_erros * settings.xp_por_erro
        xp_ganho = int(xp_bruto * settings.multiplicador_xp_simulado)
    else:
        xp_ganho = settings.xp_base_simulado_concluido

    if sessao.simulado.is_oficial:
        dificuldade_multiplicadores = {'FACIL': 1.0, 'MEDIO': 1.25, 'DIFICIL': 1.5}
        multiplicador = dificuldade_multiplicadores.get(sessao.simulado.dificuldade, 1.0)
        xp_ganho = int(xp_ganho * multiplicador)

    recompensas_ganhas, regras_info = _avaliar_e_conceder_recompensas(
        user_profile,
        RegraRecompensa.Gatilho.COMPLETAR_SIMULADO,
        contexto={'percentual_acerto': percentual_acerto}
    )
    
    xp_extra_regras = sum(info['xp_extra'] for info in regras_info)
    xp_total = xp_ganho + xp_extra_regras
    gamificacao_data.xp += xp_total

    level_up_info = _verificar_level_up(gamificacao_data)
    
    if "simulados" not in gamificacao_data.cooldowns_ativos:
        gamificacao_data.cooldowns_ativos["simulados"] = {}
    gamificacao_data.cooldowns_ativos["simulados"][simulado_id_str] = timezone.now().isoformat()
    
    gamificacao_data.save()
    
    # =======================================================================
    # INÍCIO DA ADIÇÃO: Serialização manual das recompensas
    # Esta é a parte crucial que transforma os objetos do Django em dados
    # que o JavaScript pode usar diretamente.
    # =======================================================================
    recompensas_serializadas = []
    for recompensa in recompensas_ganhas:
        recompensas_serializadas.append({
            'nome': recompensa.nome,
            'imagem_url': recompensa.imagem.url if recompensa.imagem else '', # Garante que não quebre se não houver imagem
            'raridade': recompensa.get_raridade_display(),
            'tipo': recompensa.__class__.__name__ # Retorna 'Avatar', 'Borda' ou 'Banner'
        })
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================
    
    return {
        'xp_ganho': xp_ganho,
        'regras_info': regras_info, # Já está no formato correto (lista de dicts)
        'level_up_info': level_up_info,
        'novas_recompensas': recompensas_serializadas, # Usamos a lista serializada aqui
        'percentual_acerto': round(percentual_acerto, 2)
    }


def processar_resultados_ranking(ranking_data, tipo_ranking):
    settings = GamificationSettings.load()
    gatilho = RegraRecompensa.Gatilho.RANKING_SEMANAL_TOP_N if tipo_ranking == 'semanal' else RegraRecompensa.Gatilho.RANKING_MENSAL_TOP_N
    
    for item in ranking_data:
        user_profile = item.user_profile
        posicao = item.posicao
        
        _, regras_info = _avaliar_e_conceder_recompensas(
            user_profile,
            gatilho,
            contexto={'posicao': posicao}
        )
        xp_extra = sum(info['xp_extra'] for info in regras_info)
        if xp_extra > 0:
            user_profile.gamificacao_data.xp += xp_extra
            user_profile.gamificacao_data.save()


def _avaliar_e_conceder_recompensas(user_profile, gatilho, contexto):
    regras = RegraRecompensa.objects.filter(ativo=True, gatilho=gatilho)
    recompensas_concedidas = []
    regras_info = []

    for regra in regras:
        if _verificar_condicoes(regra, contexto):
            recompensas_da_regra = []
            recompensas_a_verificar = list(regra.avatares.all()) + \
                                     list(regra.bordas.all()) + \
                                     list(regra.banners.all())

            for recompensa in recompensas_a_verificar:
                if _conceder_recompensa(user_profile, recompensa, regra):
                    recompensas_da_regra.append(recompensa)
            
            if regra.xp_extra > 0 or recompensas_da_regra:
                regras_info.append({
                    'nome': regra.nome,
                    'xp_extra': regra.xp_extra
                })
                # Associa as recompensas visuais à regra que as concedeu
                for rec in recompensas_da_regra:
                    rec.origem_da_regra = regra.nome # Adiciona um atributo temporário
                    recompensas_concedidas.append(rec)
            
    return recompensas_concedidas, regras_info
    
def _verificar_condicoes(regra, contexto):
    if not regra.condicoes: return True

    if regra.gatilho == RegraRecompensa.Gatilho.COMPLETAR_SIMULADO:
        min_acertos = regra.condicoes.get('min_acertos_percent', 0)
        if contexto.get('percentual_acerto', 0) >= min_acertos:
            return True

    if regra.gatilho in [RegraRecompensa.Gatilho.RANKING_SEMANAL_TOP_N, RegraRecompensa.Gatilho.RANKING_MENSAL_TOP_N]:
        top_n = regra.condicoes.get('top_n', 3)
        if contexto.get('posicao', float('inf')) <= top_n:
            return True
            
    return False

def _conceder_recompensa(user_profile, recompensa, regra):
    content_type = ContentType.objects.get_for_model(recompensa)
    
    if RecompensaUsuario.objects.filter(user_profile=user_profile, content_type=content_type, object_id=recompensa.id).exists():
        return False
        
    RecompensaUsuario.objects.create(
        user_profile=user_profile,
        recompensa=recompensa,
        origem=regra
    )
    
    if isinstance(recompensa, Avatar):
        AvatarUsuario.objects.get_or_create(user_profile=user_profile, avatar=recompensa)
    elif isinstance(recompensa, Borda):
        BordaUsuario.objects.get_or_create(user_profile=user_profile, borda=recompensa)
    elif isinstance(recompensa, Banner):
        BannerUsuario.objects.get_or_create(user_profile=user_profile, banner=recompensa)

    return True