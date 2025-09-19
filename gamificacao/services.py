# gamificacao/services.py

from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, Q

# Imports dos modelos
from pratica.models import RespostaUsuario
from usuarios.models import UserProfile
from .models import (
    Conquista, ConquistaUsuario, ProfileGamificacao, MetaDiariaUsuario,
    RankingSemanal, RankingMensal, TarefaAgendadaLog,
    Avatar, Borda, Banner,
    AvatarUsuario, BordaUsuario, BannerUsuario,
    GamificationSettings # <-- NOVO IMPORT
)


# =======================================================================
# CONSTANTES DE SEGURANÇA ANTI-EXPLOIT
# =======================================================================
XP_COOLDOWN_PERIODO = timedelta(hours=24) # Tempo para ganhar XP na mesma questão
MIN_TEMPO_ENTRE_RESPOSTAS = timedelta(seconds=5) # Tempo mínimo entre respostas para ganhar XP
XP_CAP_DIARIO = 500 # Teto máximo de XP ganho por dia


def calcular_xp_para_nivel(level):
    """Calcula o total de XP necessário para atingir um determinado nível."""
    return 50 * (level ** 2) + 50 * level


def processar_resposta_gamificacao(user_profile, foi_correta, questao):
    """
    Função central que processa todas as mecânicas de gamificação após uma resposta.
    Incorpora verificações de segurança para garantir um ganho de XP justo.
    Retorna um dicionário com todos os eventos que aconteceram.
    """
    # Carrega as regras de gamificação do banco de dados
    settings = GamificationSettings.load()
    
    gamificacao_data, _ = ProfileGamificacao.objects.get_or_create(user_profile=user_profile)
    hoje = date.today()
    meta_hoje, _ = MetaDiariaUsuario.objects.get_or_create(user_profile=user_profile, data=hoje)

    # 1. ATUALIZAÇÃO DE ACERTOS CONSECUTIVOS E BÔNUS
    if foi_correta:
        gamificacao_data.acertos_consecutivos += 1
        if gamificacao_data.acertos_consecutivos >= settings.acertos_consecutivos_para_bonus:
            gamificacao_data.bonus_xp_ativo = True
    else:
        gamificacao_data.acertos_consecutivos = 0
        gamificacao_data.bonus_xp_ativo = False

    # 2. CÁLCULO E VALIDAÇÃO DO GANHO DE XP
    xp_ganho = 0
    bonus_aplicado = False

    try:
        ultima_resposta = RespostaUsuario.objects.filter(usuario=user_profile.user).latest('data_resposta')
        if timezone.now() - ultima_resposta.data_resposta < MIN_TEMPO_ENTRE_RESPOSTAS:
            pass # Resposta muito rápida, ignora XP
        else:
            # Verifica cooldown e teto diário
            resposta_recente = RespostaUsuario.objects.filter(
                usuario=user_profile.user, questao=questao,
                data_resposta__gte=timezone.now() - XP_COOLDOWN_PERIODO
            ).exists()
            
            if not resposta_recente and meta_hoje.xp_ganho_dia < XP_CAP_DIARIO:
                xp_base = settings.xp_por_acerto if foi_correta else settings.xp_por_erro
                if foi_correta and gamificacao_data.bonus_xp_ativo:
                    xp_ganho = xp_base * 2
                    bonus_aplicado = True
                else:
                    xp_ganho = xp_base
    
    except RespostaUsuario.DoesNotExist:
        xp_ganho = settings.xp_por_acerto if foi_correta else settings.xp_por_erro

    gamificacao_data.xp += xp_ganho
    
    # 3. PROCESSAMENTO DA META DIÁRIA
    meta_completa_info = _processar_meta_diaria(user_profile, gamificacao_data, meta_hoje, xp_ganho, settings)
    
    # 4. VERIFICAÇÃO DE LEVEL UP
    level_up_info = _verificar_level_up(gamificacao_data)
    if level_up_info:
        _verificar_desbloqueio_recompensas(user_profile)
    
    # Salva as alterações de gamificação (XP, nível, acertos, bônus)
    gamificacao_data.save()
    
    # 5. VERIFICAÇÃO DE NOVAS CONQUISTAS
    nova_conquista = _verificar_e_registrar_conquistas(user_profile)
    if nova_conquista:
        _verificar_desbloqueio_recompensas(user_profile, conquista_ganha=nova_conquista)

    # 6. RETORNO DOS EVENTOS
    return {
        "xp_ganho": xp_ganho,
        "bonus_ativo": bonus_aplicado,
        "level_up_info": level_up_info,
        "nova_conquista": nova_conquista,
        "meta_completa_info": meta_completa_info
    }


def _processar_meta_diaria(user_profile, gamificacao_data, meta_hoje, xp_atual, settings):
    """
    Verifica e atualiza a meta diária do usuário.
    """
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
    """
    Verifica se o usuário tem XP suficiente para subir de nível.
    """
    novo_level_info = None
    xp_necessario = calcular_xp_para_nivel(gamificacao_data.level)
    
    while gamificacao_data.xp >= xp_necessario:
        gamificacao_data.level += 1
        novo_level_info = {"novo_level": gamificacao_data.level}
        xp_necessario = calcular_xp_para_nivel(gamificacao_data.level)
        
    return novo_level_info


def _verificar_desbloqueio_recompensas(user_profile, conquista_ganha=None):
    """Verifica se o usuário desbloqueou avatares, bordas ou banners."""
    nivel_atual = user_profile.gamificacao_data.level
    
    # Desbloqueios por Nível
    avatares_por_nivel = Avatar.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual)
    for avatar in avatares_por_nivel:
        AvatarUsuario.objects.get_or_create(user_profile=user_profile, avatar=avatar)
        
    bordas_por_nivel = Borda.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual)
    for borda in bordas_por_nivel:
        BordaUsuario.objects.get_or_create(user_profile=user_profile, borda=borda)
        
    banners_por_nivel = Banner.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual)
    for banner in banners_por_nivel:
        BannerUsuario.objects.get_or_create(user_profile=user_profile, banner=banner)

    # Desbloqueios por Conquista (se uma foi ganha agora)
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
    """
    Verifica todas as condições de conquista e retorna a primeira NOVA conquista.
    """
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
    """Verifica se o usuário atingiu um marco de streak."""
    current_streak = user_profile.streak_data.current_streak
    streaks_marcos = {
        'STREAK_3_DIAS': 3,
        'STREAK_7_DIAS': 7,
        'STREAK_30_DIAS': 30,
    }
    
    for chave, dias in streaks_marcos.items():
        if current_streak >= dias:
            try:
                conquista = Conquista.objects.get(chave=chave)
                _, created = ConquistaUsuario.objects.get_or_create(user_profile=user_profile, conquista=conquista)
                if created:
                    return conquista
            except Conquista.DoesNotExist:
                pass
    return None


def _verificar_conquistas_de_volume(user_profile):
    """Verifica se o usuário atingiu um marco de total de questões resolvidas."""
    total_resolvidas = RespostaUsuario.objects.filter(usuario=user_profile.user).count()
    volume_marcos = {
        'PRIMEIRA_QUESTAO': 1,
        'DEZ_QUESTOES': 10,
        'CEM_QUESTOES': 100,
    }

    for chave, quantidade in volume_marcos.items():
        if total_resolvidas >= quantidade:
            try:
                conquista = Conquista.objects.get(chave=chave)
                _, created = ConquistaUsuario.objects.get_or_create(user_profile=user_profile, conquista=conquista)
                if created:
                    return conquista
            except Conquista.DoesNotExist:
                pass
    return None


def _verificar_conquistas_de_precisao(user_profile):
    """Verifica se o usuário atingiu um marco de acertos consecutivos."""
    acertos_seguidos = user_profile.gamificacao_data.acertos_consecutivos
    precisao_marcos = {
        'PRECISAO_10': 10,
    }

    for chave, quantidade in precisao_marcos.items():
        if acertos_seguidos >= quantidade:
            try:
                conquista = Conquista.objects.get(chave=chave)
                _, created = ConquistaUsuario.objects.get_or_create(user_profile=user_profile, conquista=conquista)
                if created:
                    return conquista
            except Conquista.DoesNotExist:
                pass
    return None


def verificar_e_gerar_rankings():
    """
    Função principal que verifica se os rankings precisam ser gerados e os dispara.
    """
    _verificar_e_gerar_ranking_semanal()
    _verificar_e_gerar_ranking_mensal()


def _verificar_e_gerar_ranking_semanal():
    hoje = timezone.now()
    log_semanal, _ = TarefaAgendadaLog.objects.get_or_create(
        nome_tarefa='gerar_ranking_semanal',
        defaults={'ultima_execucao': hoje - timedelta(days=8)}
    )

    if (hoje - log_semanal.ultima_execucao).days < 7:
        return

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
    
    if log_mensal.ultima_execucao.month == hoje.month and log_mensal.ultima_execucao.year == hoje.year:
        return

    primeiro_dia_mes_atual = hoje.date().replace(day=1)
    ultimo_dia_mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
    primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)

    sucesso = _processar_e_salvar_ranking('mensal', primeiro_dia_mes_passado, ultimo_dia_mes_passado)
    if sucesso:
        log_mensal.ultima_execucao = hoje
        log_mensal.save()


def _processar_e_salvar_ranking(tipo, data_inicio, data_fim):
    """
    Lógica de cálculo e salvamento dos rankings periódicos.
    """
    respostas_no_periodo = RespostaUsuario.objects.filter(
        data_resposta__date__gte=data_inicio,
        data_resposta__date__lte=data_fim,
        usuario__is_staff=False,
        usuario__is_active=True
    )

    ranking_data = list(respostas_no_periodo
        .values('usuario_id')
        .annotate(
            acertos=Count('id', filter=Q(foi_correta=True)),
            respostas=Count('id')
        )
        .order_by('-acertos', '-respostas')
        .values('usuario_id', 'acertos', 'respostas')
    )

    if not ranking_data:
        return True

    user_profiles = UserProfile.objects.in_bulk([item['usuario_id'] for item in ranking_data])
    
    objetos_para_criar = []
    for i, item in enumerate(ranking_data):
        user_profile = user_profiles.get(item['usuario_id'])
        if not user_profile:
            continue

        if tipo == 'semanal':
            obj = RankingSemanal(
                user_profile=user_profile,
                ano=data_inicio.year,
                semana=data_inicio.isocalendar()[1],
                posicao=i + 1,
                acertos_periodo=item['acertos'],
                respostas_periodo=item['respostas']
            )
        else: # mensal
            obj = RankingMensal(
                user_profile=user_profile,
                ano=data_inicio.year,
                mes=data_inicio.month,
                posicao=i + 1,
                acertos_periodo=item['acertos'],
                respostas_periodo=item['respostas']
            )
        objetos_para_criar.append(obj)
    
    if objetos_para_criar:
        if tipo == 'semanal':
            RankingSemanal.objects.bulk_create(objetos_para_criar)
        else:
            RankingMensal.objects.bulk_create(objetos_para_criar)
            
    return True