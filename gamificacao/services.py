# gamificacao/services.py (ARQUIVO COMPLETO E REFATORADO)

from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.contenttypes.models import ContentType
from django.utils.dateparse import parse_datetime
from itertools import chain
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .models import ConquistaDiariaGlobalLog # Adicione esta importação
from django.db.models import Count, Sum


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
    # NOVOS MODELOS PARA O MOTOR DE REGRAS (DATA-DRIVEN)
    VariavelDoJogo, Condicao,
    # Modelos de Campanhas e Rankings
    Campanha, CampanhaUsuarioCompletion,
    RankingSemanal, RankingMensal, TarefaAgendadaLog
)


def calcular_xp_para_nivel(level):
    """Calcula o total de XP necessário para atingir um determinado nível."""
    return 50 * (level ** 2) + 50 * level

# gamificacao/services.py

# gamificacao/services.py



def processar_resposta_gamificacao(user, questao, alternativa_selecionada):
    """
    Motor de regras de gamificação, agora com feedback claro sobre bloqueios de XP.
    """
    settings = GamificationSettings.load()
    user_profile, _ = UserProfile.objects.get_or_create(user=user)
    gamificacao_data, _ = ProfileGamificacao.objects.get_or_create(user_profile=user_profile)
    hoje = date.today()
    meta_hoje, _ = MetaDiariaUsuario.objects.get_or_create(user_profile=user_profile, data=hoje)

    correta = (alternativa_selecionada == questao.gabarito)
    
    bloqueio_retorno = {
        "xp_ganho": 0, "moedas_ganhas": 0, "bonus_ativo": False, 
        "level_up_info": None, "nova_conquista": None, "meta_completa_info": None, 
        "correta": correta, "gabarito": questao.gabarito
    }

    try:
        ultima_resposta_geral = RespostaUsuario.objects.filter(usuario=user).latest('data_resposta')
        min_tempo = timedelta(seconds=settings.tempo_minimo_entre_respostas_segundos)
        if timezone.now() - ultima_resposta_geral.data_resposta < min_tempo:
            bloqueio_retorno['motivo_bloqueio'] = 'RESPOSTA_RAPIDA'
            return bloqueio_retorno
    except RespostaUsuario.DoesNotExist:
        pass

    resposta_anterior = RespostaUsuario.objects.filter(usuario=user, questao=questao).first()
    if resposta_anterior:
        cooldown = timedelta(hours=settings.cooldown_mesma_questao_horas)
        if timezone.now() - resposta_anterior.data_resposta < cooldown:
            bloqueio_retorno['motivo_bloqueio'] = 'COOLDOWN_QUESTAO'
            return bloqueio_retorno

    if settings.habilitar_teto_xp_diario and meta_hoje.xp_ganho_dia >= settings.teto_xp_diario:
        bloqueio_retorno['motivo_bloqueio'] = 'TETO_XP_DIARIO'
        return bloqueio_retorno

    RespostaUsuario.objects.update_or_create(
        usuario=user, questao=questao,
        defaults={'alternativa_selecionada': alternativa_selecionada, 'foi_correta': correta}
    )
    
    xp_base = 0
    if correta:
        if not resposta_anterior: xp_base = settings.xp_acerto_primeira_vez
        elif not resposta_anterior.foi_correta: xp_base = settings.xp_acerto_redencao
        else: xp_base = settings.xp_por_acerto
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
    
    moedas_ganhas = settings.moedas_por_acerto if correta else 0

    gamificacao_data.xp += xp_ganho
    gamificacao_data.moedas += moedas_ganhas
    
    if meta_hoje.questoes_resolvidas == 0:
        _avaliar_e_conceder_recompensas(user_profile, Campanha.Gatilho.PRIMEIRA_ACAO_DO_DIA, contexto={})
    
    meta_completa_info = _processar_meta_diaria(user_profile, gamificacao_data, meta_hoje, xp_ganho, settings)
    level_up_info = _verificar_level_up(gamificacao_data)
    gamificacao_data.save()
    
    nova_conquista = _avaliar_e_conceder_conquistas(user_profile)
    if level_up_info or nova_conquista:
        _verificar_desbloqueio_recompensas(user_profile, conquista_ganha=nova_conquista)

    return {
        "xp_ganho": xp_ganho, "moedas_ganhas": moedas_ganhas, "bonus_ativo": bonus_aplicado,
        "level_up_info": level_up_info, "nova_conquista": nova_conquista, "meta_completa_info": meta_completa_info,
        "correta": correta, "gabarito": questao.gabarito
    }

def _processar_meta_diaria(user_profile, gamificacao_data, meta_hoje, xp_atual, settings):
    meta_hoje.xp_ganho_dia += xp_atual
    meta_hoje.questoes_resolvidas += 1
    meta_completa_info = None

    if not meta_hoje.meta_atingida and meta_hoje.questoes_resolvidas >= settings.meta_diaria_questoes:
        meta_hoje.meta_atingida = True
        gamificacao_data.xp += settings.xp_bonus_meta_diaria
        gamificacao_data.moedas += settings.moedas_por_meta_diaria
        meta_completa_info = {"xp_bonus": settings.xp_bonus_meta_diaria, "moedas_bonus": settings.moedas_por_meta_diaria}

        # LÓGICA DO GATILHO "META DIÁRIA CONCLUÍDA" E "PRIMEIRO DO DIA"
        # 1. Dispara campanhas para TODOS que concluem a meta
        _avaliar_e_conceder_recompensas(user_profile, Campanha.Gatilho.META_DIARIA_CONCLUIDA, {})

        # 2. Tenta registrar o usuário como o primeiro do dia
        try:
            ConquistaDiariaGlobalLog.objects.create(
                user=user_profile.user, data=date.today(), tipo='META_DIARIA'
            )
            # Se conseguiu criar, ele é o primeiro! Concede o bônus especial.
            bonus_xp_primeiro = 200  # Pode vir de GamificationSettings no futuro
            bonus_moedas_primeiro = 100
            gamificacao_data.xp += bonus_xp_primeiro
            gamificacao_data.moedas += bonus_moedas_primeiro
            
            # Adiciona info ao retorno para o frontend (para exibir um toast especial)
            meta_completa_info['primeiro_do_dia'] = True
            meta_completa_info['xp_bonus_primeiro'] = bonus_xp_primeiro
            meta_completa_info['moedas_bonus_primeiro'] = bonus_moedas_primeiro
        except IntegrityError:
            # Alguém já ganhou hoje. Não faz nada.
            pass

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

# gamificacao/services.py

def _verificar_desbloqueio_recompensas(user_profile, conquista_ganha=None):
    def criar_recompensa_pendente(recompensa, origem):
        RecompensaPendente.objects.get_or_create(user_profile=user_profile, content_type=ContentType.objects.get_for_model(recompensa), object_id=recompensa.id, defaults={'origem_desbloqueio': origem})

    nivel_atual = user_profile.gamificacao_data.level
    
    # =======================================================================
    # INÍCIO DA ALTERAÇÃO: Lógica de desbloqueio direto por NÍVEL
    # Agora, a função exclui itens que também estão marcados para a loja,
    # pois esses serão desbloqueados para compra, e não concedidos diretamente.
    # =======================================================================
    recompensas_por_nivel = list(chain(
        Avatar.objects.filter(tipos_desbloqueio__nome='NIVEL', nivel_necessario__lte=nivel_atual).exclude(tipos_desbloqueio__nome='LOJA'),
        Borda.objects.filter(tipos_desbloqueio__nome='NIVEL', nivel_necessario__lte=nivel_atual).exclude(tipos_desbloqueio__nome='LOJA'),
        Banner.objects.filter(tipos_desbloqueio__nome='NIVEL', nivel_necessario__lte=nivel_atual).exclude(tipos_desbloqueio__nome='LOJA')
    ))
    for recompensa in recompensas_por_nivel:
        criar_recompensa_pendente(recompensa, f"Alcançou o Nível {recompensa.nivel_necessario}")
    # =======================================================================
    # FIM DA ALTERAÇÃO
    # =======================================================================

    # =======================================================================
    # REMOÇÃO: A lógica de desbloqueio por conquista foi removida daqui.
    # Agora, ela é tratada diretamente na função `_avaliar_e_conceder_conquistas`,
    # que lê o JSONField da conquista e concede as recompensas.
    # =======================================================================
    if conquista_ganha:
        # A lógica antiga que buscava `conquista_necessaria` foi removida.
        pass

# =======================================================================
# LÓGICA DE AVALIAÇÃO DE CONQUISTAS (TOTALMENTE REESCRITA E DINÂMICA)
# =======================================================================
# gamificacao/services.py

# ... (outras importações e funções) ...

def _avaliar_e_conceder_conquistas(user_profile):
    """
    Avalia e concede conquistas, agora com o gatilho para campanhas.
    """
    conquistas_usuario_ids = set(ConquistaUsuario.objects.filter(user_profile=user_profile).values_list('conquista_id', flat=True))
    
    conquistas_candidatas = Conquista.objects.exclude(id__in=conquistas_usuario_ids).prefetch_related(
        'pre_requisitos', 
        'condicoes__variavel'
    )

    for conquista in conquistas_candidatas:
        pre_requisitos_ids = set(p.id for p in conquista.pre_requisitos.all())
        if not pre_requisitos_ids.issubset(conquistas_usuario_ids):
            continue

        todas_condicoes_satisfeitas = True
        if not conquista.condicoes.exists():
            pass
        else:
            for condicao in conquista.condicoes.all():
                valor_atual_usuario = _obter_valor_variavel(user_profile, condicao.variavel.chave, condicao.contexto_json)
                operadores = { '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b, '==': lambda a, b: a == b, '!=': lambda a, b: a != b, }
                if not operadores[condicao.operador](valor_atual_usuario, condicao.valor):
                    todas_condicoes_satisfeitas = False
                    break
        
        if todas_condicoes_satisfeitas:
            ConquistaUsuario.objects.create(user_profile=user_profile, conquista=conquista)
            
            recompensas = conquista.recompensas
            if recompensas:
                gamificacao_data = user_profile.gamificacao_data
                gamificacao_data.xp += recompensas.get('xp', 0)
                gamificacao_data.moedas += recompensas.get('moedas', 0)
                gamificacao_data.save()
                
                for tipo, Model in [('avatares', Avatar), ('bordas', Borda), ('banners', Banner)]:
                    for recompensa_id in recompensas.get(tipo, []):
                        try:
                            item = Model.objects.get(id=recompensa_id)
                            RecompensaPendente.objects.get_or_create(
                                user_profile=user_profile,
                                content_type=ContentType.objects.get_for_model(item),
                                object_id=item.id,
                                defaults={'origem_desbloqueio': f"Prêmio da conquista '{conquista.nome}'"}
                            )
                        except Model.DoesNotExist:
                            continue
            
            # ===================================================================
            # INÍCIO DA ADIÇÃO: Dispara o novo gatilho de Campanha
            # ===================================================================
            _avaliar_e_conceder_recompensas(user_profile, Campanha.Gatilho.CONQUISTA_DESBLOQUEADA, contexto={'conquista_id': conquista.id})
            # ===================================================================
            # FIM DA ADIÇÃO
            # ===================================================================

            return conquista
            
    return None

from pratica.models import Comentario

from django.db.models import Max

def _obter_valor_variavel(user_profile, chave_variavel, contexto):
    """
    O CORAÇÃO DO MOTOR DE REGRAS. Busca o valor atual de uma estatística
    do jogador com base na chave, agora com as novas variáveis implementadas.
    """
    user = user_profile.user
    
    if chave_variavel == 'level': return user_profile.gamificacao_data.level
    if chave_variavel == 'current_streak': user_profile.streak_data.update_streak(); return user_profile.streak_data.current_streak
    if chave_variavel == 'max_streak': return user_profile.streak_data.max_streak
    if chave_variavel == 'simulados_concluidos': return SessaoSimulado.objects.filter(usuario=user, finalizado=True).count()
    if chave_variavel == 'dias_desde_ultima_pratica':
        last_date = user_profile.streak_data.last_practice_date
        if not last_date: return 999
        return (date.today() - last_date).days
    if chave_variavel == 'dias_desde_cadastro': return (timezone.now().date() - user.date_joined.date()).days
    if chave_variavel == 'acertos_consecutivos_atuais': return user_profile.gamificacao_data.acertos_consecutivos
    if chave_variavel == 'disciplinas_unicas_estudadas': return RespostaUsuario.objects.filter(usuario=user).values('questao__disciplina').distinct().count()
    if chave_variavel == 'simulados_pessoais_criados': return Simulado.objects.filter(criado_por=user, is_oficial=False).count()
    if chave_variavel == 'comentarios_criados': return Comentario.objects.filter(usuario=user, parent__isnull=True).count()
        
    # =======================================================================
    # INÍCIO DA ADIÇÃO DE NOVAS VARIÁVEIS
    # =======================================================================
    if chave_variavel == 'bancas_unicas_estudadas':
        return RespostaUsuario.objects.filter(usuario=user).values('questao__banca').distinct().count()

    if chave_variavel == 'simulados_concluidos_por_dificuldade':
        qs = SessaoSimulado.objects.filter(usuario=user, finalizado=True)
        if contexto and contexto.get('dificuldade'):
            qs = qs.filter(simulado__dificuldade=contexto['dificuldade'])
        return qs.count()

    if chave_variavel == 'melhor_percentual_acerto_em_simulado':
        sessoes = SessaoSimulado.objects.filter(usuario=user, finalizado=True)
        melhor_percentual = 0
        for sessao in sessoes:
            total_questoes = sessao.simulado.questoes.count()
            if total_questoes > 0:
                total_acertos = sessao.respostas.filter(foi_correta=True).count()
                percentual_atual = (total_acertos / total_questoes) * 100
                if percentual_atual > melhor_percentual:
                    melhor_percentual = percentual_atual
        return melhor_percentual
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================
    
    qs = RespostaUsuario.objects.filter(usuario=user)
    
    if contexto:
        if contexto.get('disciplina_id'): qs = qs.filter(questao__disciplina_id=contexto['disciplina_id'])
        if contexto.get('banca_id'): qs = qs.filter(questao__banca_id=contexto['banca_id'])
        if contexto.get('assunto_id'): qs = qs.filter(questao__assunto_id=contexto['assunto_id'])

    if chave_variavel == 'total_respostas': return qs.count()
    if chave_variavel == 'total_acertos': return qs.filter(foi_correta=True).count()
    if chave_variavel == 'percentual_acertos_geral':
        total_respostas = qs.count()
        if total_respostas == 0: return 0
        total_acertos = qs.filter(foi_correta=True).count()
        return (total_acertos / total_respostas) * 100
    if chave_variavel == 'acertos_na_semana_atual':
        hoje = date.today()
        inicio_da_semana = hoje - timedelta(days=hoje.weekday())
        return qs.filter(foi_correta=True, data_resposta__date__gte=inicio_da_semana).count()
    if chave_variavel == 'acertos_no_mes_atual':
        hoje = date.today()
        inicio_do_mes = hoje.replace(day=1)
        return qs.filter(foi_correta=True, data_resposta__date__gte=inicio_do_mes).count()
    
    return 0

# =======================================================================
# LÓGICA DE RANKING E CAMPANHAS (sem alterações)
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
    
    if not ranking_data:
        return True # Retorna sucesso se não houver dados para processar

    user_profiles_map = {up.user_id: up for up in UserProfile.objects.filter(user_id__in=[item['usuario_id'] for item in ranking_data])}
    
    objetos_para_criar = []
    for i, item in enumerate(ranking_data):
        user_profile = user_profiles_map.get(item['usuario_id'])
        if not user_profile:
            continue
            
        posicao = i + 1
        if tipo == 'semanal':
            obj = RankingSemanal(user_profile=user_profile, ano=data_inicio.year, semana=data_inicio.isocalendar()[1], posicao=posicao, acertos_periodo=item['acertos'], respostas_periodo=item['respostas'])
        else: # mensal
            obj = RankingMensal(user_profile=user_profile, ano=data_inicio.year, mes=data_inicio.month, posicao=posicao, acertos_periodo=item['acertos'], respostas_periodo=item['respostas'])
        objetos_para_criar.append(obj)
        
    if objetos_para_criar:
        # Salva os novos registros de ranking no banco
        if tipo == 'semanal':
            novos_rankings_criados = RankingSemanal.objects.bulk_create(objetos_para_criar)
        else: # mensal
            novos_rankings_criados = RankingMensal.objects.bulk_create(objetos_para_criar)
        
        # =======================================================================
        # INÍCIO DA ADIÇÃO: Dispara a distribuição de prêmios IMEDIATAMENTE.
        # =======================================================================
        # Após criar o histórico do ranking, iteramos sobre os vencedores
        # e chamamos a função que verifica as campanhas e envia os prêmios
        # para a caixa de recompensas de cada um.
        for ranking_item in novos_rankings_criados:
            processar_resultados_ranking(ranking_item, tipo)
        # =======================================================================
        # FIM DA ADIÇÃO
        # =======================================================================
            
    return True

# gamificacao/services.py

def processar_conclusao_simulado(sessao):
    """
    Processa a finalização de um simulado, concedendo XP, moedas e avaliando
    o desbloqueio de Campanhas e Conquistas.
    """
    # 1. Carrega dados e configurações iniciais
    settings = GamificationSettings.load()
    user_profile = sessao.usuario.userprofile
    gamificacao_data = user_profile.gamificacao_data
    simulado_id_str = str(sessao.simulado.id)

    # 2. Verifica a regra de cooldown para o mesmo simulado
    cooldown_timestamp_str = gamificacao_data.cooldowns_ativos.get("simulados", {}).get(simulado_id_str)
    if cooldown_timestamp_str:
        cooldown_timestamp = parse_datetime(cooldown_timestamp_str)
        cooldown_delta = timedelta(hours=settings.cooldown_mesmo_simulado_horas)
        if timezone.now() < cooldown_timestamp + cooldown_delta:
            return {'xp_ganho': 0, 'moedas_ganhas': 0, 'regras_info': [], 'level_up_info': None, 'novas_recompensas': [], 'nova_conquista': None, 'percentual_acerto': 0}
    
    # 3. Calcula as métricas de desempenho do simulado
    total_questoes = sessao.simulado.questoes.count()
    if total_questoes == 0:
        return {'xp_ganho': 0, 'moedas_ganhas': 0, 'regras_info': [], 'level_up_info': None, 'novas_recompensas': [], 'nova_conquista': None, 'percentual_acerto': 0}

    total_acertos = sessao.respostas.filter(foi_correta=True).count()
    percentual_acerto = (total_acertos / total_questoes) * 100 if total_questoes > 0 else 0
    
    # 4. Calcula o ganho base de XP e Moedas
    xp_ganho = 0
    if settings.usar_xp_dinamico_simulado:
        xp_bruto = total_acertos * settings.xp_por_acerto
        if settings.xp_dinamico_considera_erros:
            xp_bruto += (total_questoes - total_acertos) * settings.xp_por_erro
        xp_ganho = int(xp_bruto * settings.multiplicador_xp_simulado)
    else:
        xp_ganho = settings.xp_base_simulado_concluido

    if sessao.simulado.is_oficial:
        dificuldade_multiplicadores = {'FACIL': 1.0, 'MEDIO': 1.25, 'DIFICIL': 1.5}
        xp_ganho = int(xp_ganho * dificuldade_multiplicadores.get(sessao.simulado.dificuldade, 1.0))
        
    moedas_ganhas = settings.moedas_por_conclusao_simulado
    
    # =======================================================================
    # 5. AVALIA AS CAMPANHAS - LINHA ALTERADA
    # Agora passamos o ID do simulado no contexto para a verificação.
    # =======================================================================
    recompensas_ganhas, campanhas_info = _avaliar_e_conceder_recompensas(
        user_profile, 
        Campanha.Gatilho.COMPLETAR_SIMULADO, 
        contexto={
            'percentual_acerto': percentual_acerto,
            'simulado_id': sessao.simulado.id
        }
    )
    # =======================================================================
    
    # 6. Soma os bônus das campanhas aos ganhos totais
    xp_extra_campanhas = sum(info.get('xp_extra', 0) for info in campanhas_info)
    moedas_extras_campanhas = sum(info.get('moedas_extras', 0) for info in campanhas_info)
    
    gamificacao_data.xp += xp_ganho + xp_extra_campanhas
    gamificacao_data.moedas += moedas_ganhas + moedas_extras_campanhas
    
    # 7. Avalia conquistas
    nova_conquista_obj = _avaliar_e_conceder_conquistas(user_profile)
    
    # 8. Verifica level up
    level_up_info = _verificar_level_up(gamificacao_data)
    
    # 9. Atualiza cooldown e salva
    if "simulados" not in gamificacao_data.cooldowns_ativos: 
        gamificacao_data.cooldowns_ativos["simulados"] = {}
    gamificacao_data.cooldowns_ativos["simulados"][simulado_id_str] = timezone.now().isoformat()
    gamificacao_data.save()
    
    # 10. Prepara o retorno para o frontend
    recompensas_serializadas = [{'nome': r.nome, 'imagem_url': r.imagem.url if r.imagem else '', 'raridade': r.get_raridade_display(), 'tipo': r.__class__.__name__} for r in recompensas_ganhas]
    
    nova_conquista_serializada = None
    if nova_conquista_obj:
        nova_conquista_serializada = {
            'id': nova_conquista_obj.id, 'nome': nova_conquista_obj.nome, 'descricao': nova_conquista_obj.descricao,
            'icone': nova_conquista_obj.icone, 'cor': nova_conquista_obj.cor
        }
    
    return {
        'xp_ganho': xp_ganho + xp_extra_campanhas,
        'moedas_ganhas': moedas_ganhas + moedas_extras_campanhas,
        'regras_info': campanhas_info,
        'level_up_info': level_up_info,
        'novas_recompensas': recompensas_serializadas,
        'nova_conquista': nova_conquista_serializada,
        'percentual_acerto': round(percentual_acerto, 2)
    }


def _avaliar_e_conceder_recompensas(user_profile, gatilho, contexto):
    """
    Avalia e concede recompensas de campanhas, com a nova lógica para
    filtrar por simulado específico.
    """
    agora = timezone.now()
    regras = Campanha.objects.filter(
        ativo=True, 
        gatilho=gatilho, 
        data_inicio__lte=agora
    ).filter(Q(data_fim__gte=agora) | Q(data_fim__isnull=True))
    
    recompensas_concedidas = []
    regras_info = []

    for regra in regras:
        # =======================================================================
        # ADIÇÃO: Filtro para campanhas de simulado específico
        # =======================================================================
        if gatilho == Campanha.Gatilho.COMPLETAR_SIMULADO and regra.simulado_especifico:
            simulado_concluido_id = contexto.get('simulado_id')
            # Se o ID do simulado concluído não for o mesmo da regra, pula para a próxima regra
            if not simulado_concluido_id or simulado_concluido_id != regra.simulado_especifico.id:
                continue
        # =======================================================================

        ciclo_id = 'geral'
        if regra.tipo_recorrencia == Campanha.TipoRecorrencia.SEMANAL:
            ciclo_id = agora.strftime('%Y-W%U')
        elif regra.tipo_recorrencia == Campanha.TipoRecorrencia.MENSAL:
            ciclo_id = agora.strftime('%Y-%m')
        
        if regra.tipo_recorrencia != Campanha.TipoRecorrencia.UNICA:
            if CampanhaUsuarioCompletion.objects.filter(user_profile=user_profile, campanha=regra, ciclo_id=ciclo_id).exists():
                continue
        
        for grupo in regra.grupos_de_condicoes:
            if _verificar_condicoes_de_grupo(grupo, contexto, user_profile):
                xp_extra = grupo.get('xp_extra', 0)
                moedas_extras = grupo.get('moedas_extras', 0)
                recompensas_do_grupo = []

                for tipo_recompensa, Model in [('avatares', Avatar), ('bordas', Borda), ('banners', Banner)]:
                    for recompensa_id in grupo.get(tipo_recompensa, []):
                        try:
                            recompensa = Model.objects.get(id=recompensa_id)
                            if _conceder_recompensa(user_profile, recompensa, regra):
                                recompensas_do_grupo.append(recompensa)
                        except Model.DoesNotExist:
                            continue
                
                if xp_extra > 0 or moedas_extras > 0 or recompensas_do_grupo:
                    regras_info.append({'nome': regra.nome, 'xp_extra': xp_extra, 'moedas_extras': moedas_extras})
                    recompensas_concedidas.extend(recompensas_do_grupo)
                
                if regra.tipo_recorrencia != Campanha.TipoRecorrencia.UNICA:
                     CampanhaUsuarioCompletion.objects.get_or_create(
                         user_profile=user_profile, 
                         campanha=regra, 
                         ciclo_id=ciclo_id
                     )
                break 
    return recompensas_concedidas, regras_info

    
def processar_resultados_ranking(ranking_data, tipo_ranking):
    gatilho = Campanha.Gatilho.RANKING_SEMANAL_CONCLUIDO if tipo_ranking == 'semanal' else Campanha.Gatilho.RANKING_MENSAL_CONCLUIDO
    for item in ranking_data:
        _avaliar_e_conceder_recompensas(item.user_profile, gatilho, contexto={'posicao': item.posicao})




def _verificar_condicoes_de_grupo(grupo, contexto, user_profile):
    """
    Função refatorada para usar o motor de regras de VariaveisDoJogo,
    agora com suporte a contexto de disciplina também para campanhas.
    """
    # 1. Verificações legadas (baseadas em contexto do evento)
    posicao = contexto.get('posicao')
    percentual_acerto = contexto.get('percentual_acerto')

    if grupo.get('condicao_posicao_exata'):
        if not (posicao and posicao == grupo['condicao_posicao_exata']): return False
            
    if grupo.get('condicao_posicao_ate'):
        if not (posicao and posicao <= grupo['condicao_posicao_ate']): return False

    if grupo.get('condicao_min_acertos_percent'):
        if not (percentual_acerto is not None and percentual_acerto >= grupo['condicao_min_acertos_percent']): return False

    # 2. Verificação dinâmica baseada em VariaveisDoJogo
    condicoes_dinamicas = grupo.get('condicoes', [])
    if condicoes_dinamicas:
        variaveis_map = {v.id: v.chave for v in VariavelDoJogo.objects.all()}

        for condicao in condicoes_dinamicas:
            try:
                variavel_id = condicao['variavel_id']
                variavel_chave = variaveis_map.get(variavel_id)
                if not variavel_chave: return False

                # =======================================================================
                # ALTERAÇÃO PRINCIPAL AQUI: Passa o contexto da condição para o motor.
                # =======================================================================
                contexto_condicao = condicao.get('contexto', {})
                valor_atual_usuario = _obter_valor_variavel(user_profile, variavel_chave, contexto_condicao)
                # =======================================================================
                
                valor_condicao = condicao['valor']
                operador = condicao['operador']
                
                operadores = { '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b, '==': lambda a, b: a == b }
                
                if not operadores[operador](valor_atual_usuario, valor_condicao):
                    return False
            except (KeyError, TypeError):
                return False
                
    return True


