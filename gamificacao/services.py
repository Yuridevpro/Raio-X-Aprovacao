# gamificacao/services.py (ARQUIVO COMPLETO E CORRIGIDO)

from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.contenttypes.models import ContentType
from django.utils.dateparse import parse_datetime
from itertools import chain

# Importações de Modelos
from pratica.models import RespostaUsuario
from usuarios.models import UserProfile
from simulados.models import SessaoSimulado
from .models import (
    # Modelos Principais
    GamificationSettings, ProfileGamificacao, ProfileStreak, MetaDiariaUsuario,
    # Modelos de Recompensa
    Avatar, Borda, Banner, RecompensaPendente,
    AvatarUsuario, BordaUsuario, BannerUsuario, RecompensaUsuario,
    # Modelos de Conquistas e Trilhas
    Conquista, ConquistaUsuario,
    # Modelos de Condições Dinâmicas
    CondicaoVolumeQuestoes, CondicaoStreak,
    # Modelos de Campanhas e Rankings
    Campanha, CampanhaUsuarioCompletion,
    RankingSemanal, RankingMensal, TarefaAgendadaLog
)


def calcular_xp_para_nivel(level):
    """Calcula o total de XP necessário para atingir um determinado nível."""
    return 50 * (level ** 2) + 50 * level

def processar_resposta_gamificacao(user, questao, alternativa_selecionada):
    """
    Motor de regras de gamificação. Avalia uma resposta de questão, aplica regras de
    cooldown e anti-farming, concede XP e moedas, e verifica o desbloqueio de
    conquistas e recompensas.
    """
    # 1. Carrega as configurações e os perfis de gamificação do usuário
    settings = GamificationSettings.load()
    user_profile, _ = UserProfile.objects.get_or_create(user=user)
    gamificacao_data, _ = ProfileGamificacao.objects.get_or_create(user_profile=user_profile)
    hoje = date.today()
    meta_hoje, _ = MetaDiariaUsuario.objects.get_or_create(user_profile=user_profile, data=hoje)

    correta = (alternativa_selecionada == questao.gabarito)

    # 2. Verifica as regras de anti-farming (cooldowns e limites)
    try:
        ultima_resposta_geral = RespostaUsuario.objects.filter(usuario=user).latest('data_resposta')
        min_tempo = timedelta(seconds=settings.tempo_minimo_entre_respostas_segundos)
        if timezone.now() - ultima_resposta_geral.data_resposta < min_tempo:
            return {"xp_ganho": 0, "moedas_ganhas": 0, "bonus_ativo": False, "level_up_info": None, "nova_conquista": None, "meta_completa_info": None, "correta": correta, "gabarito": questao.gabarito}
    except RespostaUsuario.DoesNotExist:
        pass

    resposta_anterior = RespostaUsuario.objects.filter(usuario=user, questao=questao).first()
    if resposta_anterior:
        cooldown = timedelta(hours=settings.cooldown_mesma_questao_horas)
        if timezone.now() - resposta_anterior.data_resposta < cooldown:
            return {"xp_ganho": 0, "moedas_ganhas": 0, "bonus_ativo": False, "level_up_info": None, "nova_conquista": None, "meta_completa_info": None, "correta": correta, "gabarito": questao.gabarito}

    if settings.habilitar_teto_xp_diario and meta_hoje.xp_ganho_dia >= settings.teto_xp_diario:
        return {"xp_ganho": 0, "moedas_ganhas": 0, "bonus_ativo": False, "level_up_info": None, "nova_conquista": None, "meta_completa_info": None, "correta": correta, "gabarito": questao.gabarito}

    # 3. Se todas as verificações passaram, salva a resposta do usuário
    RespostaUsuario.objects.update_or_create(
        usuario=user, questao=questao,
        defaults={'alternativa_selecionada': alternativa_selecionada, 'foi_correta': correta}
    )
    
    # 4. Calcula o XP base com base no cenário da resposta
    xp_base = 0
    if correta:
        if not resposta_anterior: xp_base = settings.xp_acerto_primeira_vez
        elif not resposta_anterior.foi_correta: xp_base = settings.xp_acerto_redencao
        else: xp_base = settings.xp_por_acerto
    else:
        xp_base = settings.xp_por_erro

    # 5. Gerencia o bônus de acertos consecutivos
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
    
    # 6. Calcula as moedas ganhas
    moedas_ganhas = settings.moedas_por_acerto if correta else 0

    # 7. Atualiza os dados do perfil de gamificação
    gamificacao_data.xp += xp_ganho
    gamificacao_data.moedas += moedas_ganhas
    
    meta_completa_info = _processar_meta_diaria(user_profile, gamificacao_data, meta_hoje, xp_ganho, settings)
    level_up_info = _verificar_level_up(gamificacao_data)
    gamificacao_data.save()
    
    # 8. Avalia o desbloqueio de recompensas e conquistas
    nova_conquista = _avaliar_e_conceder_conquistas(user_profile)
    if level_up_info or nova_conquista:
        _verificar_desbloqueio_recompensas(user_profile, conquista_ganha=nova_conquista)

    # 9. Retorna um dicionário completo com todos os eventos para o frontend
    return {
        "xp_ganho": xp_ganho,
        "moedas_ganhas": moedas_ganhas,
        "bonus_ativo": bonus_aplicado,
        "level_up_info": level_up_info,
        "nova_conquista": nova_conquista,
        "meta_completa_info": meta_completa_info,
        "correta": correta,
        "gabarito": questao.gabarito
    }

def _processar_meta_diaria(user_profile, gamificacao_data, meta_hoje, xp_atual, settings):
    meta_hoje.xp_ganho_dia += xp_atual
    meta_hoje.questoes_resolvidas += 1
    meta_completa_info = None
    if not meta_hoje.meta_atingida and meta_hoje.questoes_resolvidas >= settings.meta_diaria_questoes:
        meta_hoje.meta_atingida = True
        gamificacao_data.xp += settings.xp_bonus_meta_diaria
        gamificacao_data.moedas += settings.moedas_por_meta_diaria
        meta_completa_info = {"xp_bonus": settings.xp_bonus_meta_diaria, "moedas_bonus": settings.moedas_por_meta_diaria, "total_questoes": settings.meta_diaria_questoes}
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
    def criar_recompensa_pendente(recompensa, origem):
        RecompensaPendente.objects.get_or_create(user_profile=user_profile, content_type=ContentType.objects.get_for_model(recompensa), object_id=recompensa.id, defaults={'origem_desbloqueio': origem})

    nivel_atual = user_profile.gamificacao_data.level
    recompensas_por_nivel = list(chain(Avatar.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual), Borda.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual), Banner.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual)))
    for recompensa in recompensas_por_nivel:
        criar_recompensa_pendente(recompensa, f"Alcançou o Nível {recompensa.nivel_necessario}")

    if conquista_ganha:
        recompensas_por_conquista = list(chain(Avatar.objects.filter(tipo_desbloqueio='CONQUISTA', conquista_necessaria=conquista_ganha), Borda.objects.filter(tipo_desbloqueio='CONQUISTA', conquista_necessaria=conquista_ganha), Banner.objects.filter(tipo_desbloqueio='CONQUISTA', conquista_necessaria=conquista_ganha)))
        for recompensa in recompensas_por_conquista:
            criar_recompensa_pendente(recompensa, f"Desbloqueou a conquista '{conquista_ganha.nome}'")

# =======================================================================
# LÓGICA DE AVALIAÇÃO DE CONQUISTAS (REESCRITA)
# =======================================================================
def _avaliar_e_conceder_conquistas(user_profile):
    """
    Verifica todas as conquistas que o usuário ainda não possui e que são
    desbloqueáveis, avaliando suas condições dinâmicas.
    """
    conquistas_usuario_ids = set(ConquistaUsuario.objects.filter(user_profile=user_profile).values_list('conquista_id', flat=True))
    conquistas_candidatas = Conquista.objects.exclude(id__in=conquistas_usuario_ids).prefetch_related('pre_requisitos', 'condicoes_volume', 'condicoes_streak')

    for conquista in conquistas_candidatas:
        pre_requisitos_ids = set(conquista.pre_requisitos.values_list('id', flat=True))
        if not pre_requisitos_ids.issubset(conquistas_usuario_ids):
            continue

        todas_condicoes_satisfeitas = True
        
        # A propriedade conquista.condicoes agora reúne todas as relações genéricas
        condicoes_da_conquista = conquista.condicoes
        if condicoes_da_conquista:
            for condicao in condicoes_da_conquista:
                if not _verificar_condicao_especifica(user_profile, condicao):
                    todas_condicoes_satisfeitas = False
                    break
        
        if todas_condicoes_satisfeitas:
            ConquistaUsuario.objects.create(user_profile=user_profile, conquista=conquista)
            recompensas = conquista.recompensas
            if recompensas:
                user_profile.gamificacao_data.xp += recompensas.get('xp', 0)
                user_profile.gamificacao_data.moedas += recompensas.get('moedas', 0)
                user_profile.gamificacao_data.save()
                for tipo, Model in [('avatares', Avatar), ('bordas', Borda), ('banners', Banner)]:
                    for recompensa_id in recompensas.get(tipo, []):
                        try:
                            item = Model.objects.get(id=recompensa_id)
                            RecompensaPendente.objects.get_or_create(user_profile=user_profile, content_type=ContentType.objects.get_for_model(item), object_id=item.id, defaults={'origem_desbloqueio': f"Prêmio da conquista '{conquista.nome}'"})
                        except Model.DoesNotExist:
                            continue
            return conquista
    return None

def _verificar_condicao_especifica(user_profile, condicao):
    """Roteador que chama a função de verificação correta com base no tipo da condição."""
    if isinstance(condicao, CondicaoVolumeQuestoes):
        return _verificar_condicao_volume(user_profile, condicao)
    if isinstance(condicao, CondicaoStreak):
        return _verificar_condicao_streak(user_profile, condicao)
    return False

def _verificar_condicao_volume(user_profile, condicao):
    """Verifica se o usuário atingiu um volume de questões resolvidas."""
    qs = RespostaUsuario.objects.filter(usuario=user_profile.user)
    if condicao.disciplina: qs = qs.filter(questao__disciplina=condicao.disciplina)
    if condicao.assunto: qs = qs.filter(questao__assunto=condicao.assunto)
    if condicao.banca: qs = qs.filter(questao__banca=condicao.banca)
    total_resolvidas = qs.count()
    if total_resolvidas < condicao.quantidade:
        return False
    if condicao.percentual_acerto_minimo > 0:
        total_acertos = qs.filter(foi_correta=True).count()
        percentual_atual = (total_acertos / total_resolvidas) * 100 if total_resolvidas > 0 else 0
        if percentual_atual < condicao.percentual_acerto_minimo:
            return False
    return True

def _verificar_condicao_streak(user_profile, condicao):
    """Verifica se o usuário atingiu uma sequência de dias."""
    streak_atual = user_profile.streak_data.current_streak
    return streak_atual >= condicao.dias_consecutivos

# =======================================================================
# LÓGICA DE RANKING E CAMPANHAS
# =======================================================================
def verificar_e_gerar_rankings():
    _verificar_e_gerar_ranking_semanal()
    _verificar_e_gerar_ranking_mensal()

def _verificar_e_gerar_ranking_semanal():
    hoje = timezone.now()
    log_semanal, _ = TarefaAgendadaLog.objects.get_or_create(nome_tarefa='gerar_ranking_semanal', defaults={'ultima_execucao': hoje - timedelta(days=8)})
    if (hoje - log_semanal.ultima_execucao).days < 7: return
    semana_passada_data = hoje.date() - timedelta(days=7)
    ano, semana, _ = semana_passada_data.isocalendar()
    start_of_week = date.fromisocalendar(ano, semana, 1)
    end_of_week = start_of_week + timedelta(days=6)
    if _processar_e_salvar_ranking('semanal', start_of_week, end_of_week):
        log_semanal.ultima_execucao = hoje
        log_semanal.save()

def _verificar_e_gerar_ranking_mensal():
    hoje = timezone.now()
    log_mensal, _ = TarefaAgendadaLog.objects.get_or_create(nome_tarefa='gerar_ranking_mensal', defaults={'ultima_execucao': hoje - timedelta(days=32)})
    if log_mensal.ultima_execucao.month == hoje.month and log_mensal.ultima_execucao.year == hoje.year: return
    primeiro_dia_mes_atual = hoje.date().replace(day=1)
    ultimo_dia_mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
    primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)
    if _processar_e_salvar_ranking('mensal', primeiro_dia_mes_passado, ultimo_dia_mes_passado):
        log_mensal.ultima_execucao = hoje
        log_mensal.save()

def _processar_e_salvar_ranking(tipo, data_inicio, data_fim):
    respostas_no_periodo = RespostaUsuario.objects.filter(data_resposta__date__gte=data_inicio, data_resposta__date__lte=data_fim, usuario__is_staff=False, usuario__is_active=True)
    ranking_data = list(respostas_no_periodo.values('usuario_id').annotate(acertos=Count('id', filter=Q(foi_correta=True)), respostas=Count('id')).order_by('-acertos', '-respostas').values('usuario_id', 'acertos', 'respostas'))
    if not ranking_data: return True
    user_profiles = UserProfile.objects.in_bulk([item['usuario_id'] for item in ranking_data])
    objetos_para_criar = []
    for i, item in enumerate(ranking_data):
        user_profile = user_profiles.get(item['usuario_id'])
        if not user_profile: continue
        if tipo == 'semanal':
            obj = RankingSemanal(user_profile=user_profile, ano=data_inicio.year, semana=data_inicio.isocalendar()[1], posicao=i + 1, acertos_periodo=item['acertos'], respostas_periodo=item['respostas'])
        else:
            obj = RankingMensal(user_profile=user_profile, ano=data_inicio.year, mes=data_inicio.month, posicao=i + 1, acertos_periodo=item['acertos'], respostas_periodo=item['respostas'])
        objetos_para_criar.append(obj)
    if objetos_para_criar:
        if tipo == 'semanal': RankingSemanal.objects.bulk_create(objetos_para_criar)
        else: RankingMensal.objects.bulk_create(objetos_para_criar)
    return True

def processar_conclusao_simulado(sessao):
    settings = GamificationSettings.load()
    user, user_profile, gamificacao_data = sessao.usuario, sessao.usuario.userprofile, sessao.usuario.userprofile.gamificacao_data
    simulado_id_str = str(sessao.simulado.id)

    cooldown_timestamp_str = gamificacao_data.cooldowns_ativos.get("simulados", {}).get(simulado_id_str)
    if cooldown_timestamp_str:
        cooldown_timestamp = parse_datetime(cooldown_timestamp_str)
        cooldown_delta = timedelta(hours=settings.cooldown_mesmo_simulado_horas)
        if timezone.now() < cooldown_timestamp + cooldown_delta:
            return {'xp_ganho': 0, 'moedas_ganhas': 0, 'regras_info': [], 'level_up_info': None, 'novas_recompensas': [], 'percentual_acerto': 0}
    
    total_questoes = sessao.simulado.questoes.count()
    if total_questoes == 0: return {}

    total_acertos = sessao.respostas.filter(foi_correta=True).count()
    percentual_acerto = (total_acertos / total_questoes) * 100 if total_questoes > 0 else 0
    
    xp_ganho = 0
    if settings.usar_xp_dinamico_simulado:
        xp_bruto = total_acertos * settings.xp_por_acerto
        if settings.xp_dinamico_considera_erros: xp_bruto += (total_questoes - total_acertos) * settings.xp_por_erro
        xp_ganho = int(xp_bruto * settings.multiplicador_xp_simulado)
    else:
        xp_ganho = settings.xp_base_simulado_concluido

    if sessao.simulado.is_oficial:
        dificuldade_multiplicadores = {'FACIL': 1.0, 'MEDIO': 1.25, 'DIFICIL': 1.5}
        xp_ganho = int(xp_ganho * dificuldade_multiplicadores.get(sessao.simulado.dificuldade, 1.0))
        
    moedas_ganhas = settings.moedas_por_conclusao_simulado
    recompensas_ganhas, regras_info = _avaliar_e_conceder_recompensas(user_profile, Campanha.Gatilho.COMPLETAR_SIMULADO, contexto={'percentual_acerto': percentual_acerto})
    
    gamificacao_data.xp += xp_ganho + sum(info['xp_extra'] for info in regras_info)
    gamificacao_data.moedas += moedas_ganhas + sum(info['moedas_extras'] for info in regras_info)
    level_up_info = _verificar_level_up(gamificacao_data)
    
    if "simulados" not in gamificacao_data.cooldowns_ativos: gamificacao_data.cooldowns_ativos["simulados"] = {}
    gamificacao_data.cooldowns_ativos["simulados"][simulado_id_str] = timezone.now().isoformat()
    gamificacao_data.save()
    
    recompensas_serializadas = [{'nome': r.nome, 'imagem_url': r.imagem.url if r.imagem else '', 'raridade': r.get_raridade_display(), 'tipo': r.__class__.__name__} for r in recompensas_ganhas]
    
    return {
        'xp_ganho': xp_ganho, 'moedas_ganhas': moedas_ganhas, 'regras_info': regras_info,
        'level_up_info': level_up_info, 'novas_recompensas': recompensas_serializadas,
        'percentual_acerto': round(percentual_acerto, 2)
    }

def processar_resultados_ranking(ranking_data, tipo_ranking):
    gatilho = Campanha.Gatilho.RANKING_SEMANAL_CONCLUIDO if tipo_ranking == 'semanal' else Campanha.Gatilho.RANKING_MENSAL_CONCLUIDO
    for item in ranking_data:
        _avaliar_e_conceder_recompensas(item.user_profile, gatilho, contexto={'posicao': item.posicao})

def _avaliar_e_conceder_recompensas(user_profile, gatilho, contexto):
    agora = timezone.now()
    regras = Campanha.objects.filter(ativo=True, gatilho=gatilho, data_inicio__lte=agora).filter(Q(data_fim__gte=agora) | Q(data_fim__isnull=True))
    recompensas_concedidas = []; regras_info = []

    for regra in regras:
        ciclo_id = 'geral' # Para unicas por usuário
        if regra.tipo_recorrencia == Campanha.TipoRecorrencia.SEMANAL: ciclo_id = agora.strftime('%Y-W%U')
        elif regra.tipo_recorrencia == Campanha.TipoRecorrencia.MENSAL: ciclo_id = agora.strftime('%Y-%m')
        elif regra.tipo_recorrencia == Campanha.TipoRecorrencia.DIARIA: ciclo_id = agora.strftime('%Y-%m-%d')
        
        if regra.tipo_recorrencia != Campanha.TipoRecorrencia.SEMPRE:
            if CampanhaUsuarioCompletion.objects.filter(user_profile=user_profile, campanha=regra, ciclo_id=ciclo_id).exists():
                continue
        
        for grupo in regra.grupos_de_condicoes:
            if _verificar_condicoes_de_grupo(grupo, contexto):
                xp_extra = grupo.get('xp_extra', 0); moedas_extras = grupo.get('moedas_extras', 0)
                recompensas_do_grupo = []
                for tipo_recompensa, Model in [('avatares', Avatar), ('bordas', Borda), ('banners', Banner)]:
                    for recompensa_id in grupo.get(tipo_recompensa, []):
                        try:
                            recompensa = Model.objects.get(id=recompensa_id)
                            if _conceder_recompensa(user_profile, recompensa, regra):
                                recompensas_do_grupo.append(recompensa)
                        except Model.DoesNotExist: continue
                
                if xp_extra > 0 or moedas_extras > 0 or recompensas_do_grupo:
                    regras_info.append({'nome': regra.nome, 'xp_extra': xp_extra, 'moedas_extras': moedas_extras})
                    recompensas_concedidas.extend(recompensas_do_grupo)

                if regra.tipo_recorrencia != Campanha.TipoRecorrencia.SEMPRE:
                    CampanhaUsuarioCompletion.objects.create(user_profile=user_profile, campanha=regra, ciclo_id=ciclo_id)
                break
    return recompensas_concedidas, regras_info
    
def _verificar_condicoes_de_grupo(grupo, contexto):
    posicao, percentual_acerto = contexto.get('posicao'), contexto.get('percentual_acerto')
    if 'condicao_posicao_exata' in grupo and grupo['condicao_posicao_exata'] > 0 and posicao != grupo['condicao_posicao_exata']: return False
    if 'condicao_posicao_ate' in grupo and grupo['condicao_posicao_ate'] > 0 and not (posicao and posicao <= grupo['condicao_posicao_ate']): return False
    if 'condicao_min_acertos_percent' in grupo and grupo['condicao_min_acertos_percent'] > 0 and not (percentual_acerto is not None and percentual_acerto >= grupo['condicao_min_acertos_percent']): return False
    return True

def _conceder_recompensa(user_profile, recompensa, regra):
    _, created = RecompensaPendente.objects.get_or_create(user_profile=user_profile, content_type=ContentType.objects.get_for_model(recompensa), object_id=recompensa.id, defaults={'origem_desbloqueio': f"Prêmio da campanha '{regra.nome}'"})
    return created