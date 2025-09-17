# gamificacao/services.py

from pratica.models import RespostaUsuario
from .models import Conquista, ConquistaUsuario, ProfileGamificacao

from .models import Conquista, ConquistaUsuario, ProfileGamificacao, MetaDiariaUsuario
from .models import RankingSemanal, RankingMensal, TarefaAgendadaLog
from pratica.models import RespostaUsuario
from usuarios.models import UserProfile
# =======================================================================
# CONSTANTES DE GAMIFICAÇÃO (Centraliza as regras do jogo)
# =======================================================================
from .models import RankingSemanal, RankingMensal
from django.utils import timezone
from datetime import date, timedelta
from usuarios.models import UserProfile
from django.db.models import Count, Q, F, Window
from django.db.models.functions import Rank


XP_POR_ACERTO = 10
XP_POR_ERRO = 1
XP_BONUS_META_DIARIA = 50
META_DIARIA_QUESTOES = 15

def calcular_xp_para_nivel(level):
    return 50 * (level ** 2) + 50 * level

from .models import Avatar, Borda, AvatarUsuario, BordaUsuario, Conquista


def processar_resposta_gamificacao(user_profile, foi_correta):
    """
    Função central que processa todas as mecânicas de gamificação após uma resposta.
    Retorna um dicionário com todos os eventos que aconteceram.
    """
    gamificacao_data, _ = ProfileGamificacao.objects.get_or_create(user_profile=user_profile)
    
    # 1. ATUALIZAR ACERTOS CONSECUTIVOS
    if foi_correta:
        gamificacao_data.acertos_consecutivos += 1
    else:
        gamificacao_data.acertos_consecutivos = 0
    
    # 2. Adicionar XP
    xp_ganho = XP_POR_ACERTO if foi_correta else XP_POR_ERRO
    gamificacao_data.xp += xp_ganho
    
    # 3. Processar Meta Diária e Adicionar XP Bônus, se aplicável
    meta_completa_info = _processar_meta_diaria(user_profile, gamificacao_data)
    
    # 4. Verificar se subiu de nível (após todos os ganhos de XP)
    level_up_info = _verificar_level_up(gamificacao_data)

    # =======================================================================
    # ADIÇÃO 1: VERIFICAÇÃO DE RECOMPENSAS APÓS LEVEL UP
    # =======================================================================
    # Se a verificação de level up retornou um novo nível, chamamos a função
    # que verifica se algum Avatar ou Borda foi desbloqueado por atingir esse nível.
    if level_up_info:
        _verificar_desbloqueio_recompensas(user_profile)
    # =======================================================================
    
    # Salva as alterações de XP, Nível e Acertos Consecutivos no banco
    gamificacao_data.save()
    
    # 5. Verificar novas conquistas
    nova_conquista = _verificar_e_registrar_conquistas(user_profile)

    # =======================================================================
    # ADIÇÃO 2: VERIFICAÇÃO DE RECOMPENSAS APÓS GANHAR CONQUISTA
    # =======================================================================
    # Se a verificação de conquistas encontrou uma nova, chamamos a mesma função
    # de recompensa, passando a conquista específica como parâmetro.
    if nova_conquista:
        _verificar_desbloqueio_recompensas(user_profile, conquista_ganha=nova_conquista)
    # =======================================================================

    return {
        "xp_ganho": xp_ganho,
        "level_up_info": level_up_info,
        "nova_conquista": nova_conquista,
        "meta_completa_info": meta_completa_info
    }

def _verificar_desbloqueio_recompensas(user_profile, conquista_ganha=None):
    """Verifica se o usuário desbloqueou avatares ou bordas."""
    nivel_atual = user_profile.gamificacao_data.level
    
    # Desbloqueios por Nível
    avatares_por_nivel = Avatar.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual)
    for avatar in avatares_por_nivel:
        AvatarUsuario.objects.get_or_create(user_profile=user_profile, avatar=avatar)
        
    bordas_por_nivel = Borda.objects.filter(tipo_desbloqueio='NIVEL', nivel_necessario__lte=nivel_atual)
    for borda in bordas_por_nivel:
        BordaUsuario.objects.get_or_create(user_profile=user_profile, borda=borda)

    # Desbloqueios por Conquista (se uma foi ganha agora)
    if conquista_ganha:
        avatares_por_conquista = Avatar.objects.filter(tipo_desbloqueio='CONQUISTA', conquista_necessaria=conquista_ganha)
        for avatar in avatares_por_conquista:
            AvatarUsuario.objects.get_or_create(user_profile=user_profile, avatar=avatar)
            
        bordas_por_conquista = Borda.objects.filter(tipo_desbloqueio='CONQUISTA', conquista_necessaria=conquista_ganha)
        for borda in bordas_por_conquista:
            BordaUsuario.objects.get_or_create(user_profile=user_profile, borda=borda)



def _processar_meta_diaria(user_profile, gamificacao_data):
    """
    Verifica e atualiza a meta diária do usuário.
    Retorna informações sobre a meta se ela for completada nesta ação.
    """
    hoje = date.today()
    meta_hoje, created = MetaDiariaUsuario.objects.get_or_create(
        user_profile=user_profile,
        data=hoje
    )

    # Se a meta já foi atingida hoje, não faz nada.
    if meta_hoje.meta_atingida:
        return None

    meta_hoje.questoes_resolvidas += 1
    
    meta_completa_info = None
    # Verifica se a meta foi atingida AGORA
    if meta_hoje.questoes_resolvidas >= META_DIARIA_QUESTOES:
        meta_hoje.meta_atingida = True
        gamificacao_data.xp += XP_BONUS_META_DIARIA # Adiciona o bônus de XP
        meta_completa_info = {
            "xp_bonus": XP_BONUS_META_DIARIA,
            "total_questoes": META_DIARIA_QUESTOES
        }

    meta_hoje.save()
    return meta_completa_info



def _verificar_level_up(gamificacao_data):
    """
    Verifica se o usuário tem XP suficiente para subir de nível.
    Pode subir múltiplos níveis de uma vez.
    """
    novo_level_info = None
    xp_necessario = calcular_xp_para_nivel(gamificacao_data.level)
    
    # Loop para o caso de o usuário ganhar XP suficiente para subir vários níveis
    while gamificacao_data.xp >= xp_necessario:
        gamificacao_data.level += 1
        novo_level_info = { "novo_level": gamificacao_data.level }
        xp_necessario = calcular_xp_para_nivel(gamificacao_data.level)
        
    return novo_level_info

def _verificar_e_registrar_conquistas(user_profile):
    """
    Verifica todas as condições de conquista e retorna a primeira NOVA conquista.
    """
    verificadores = [
        _verificar_conquistas_de_streak,
        _verificar_conquistas_de_volume,
        _verificar_conquistas_de_precisao, # <-- Adicionado aqui
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
    # Acessa o dado de gamificação que já foi atualizado na função principal
    acertos_seguidos = user_profile.gamificacao_data.acertos_consecutivos
    precisao_marcos = {
        'PRECISAO_10': 10,
        # Você pode adicionar mais marcos aqui no futuro (ex: 'PRECISAO_25': 25)
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
    Esta função será chamada pela view do ranking.
    """
    _verificar_e_gerar_ranking_semanal()
    _verificar_e_gerar_ranking_mensal()

def _verificar_e_gerar_ranking_semanal():
    hoje = timezone.now()
    log_semanal, _ = TarefaAgendadaLog.objects.get_or_create(
        nome_tarefa='gerar_ranking_semanal',
        defaults={'ultima_execucao': hoje - timedelta(days=8)} # Garante que rode na 1ª vez
    )

    # Se a última execução foi há menos de 7 dias, não faz nada.
    if (hoje - log_semanal.ultima_execucao).days < 7:
        return

    # A tarefa precisa rodar
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
        defaults={'ultima_execucao': hoje - timedelta(days=32)} # Garante que rode na 1ª vez
    )
    
    # Se a última execução foi no mesmo mês, não faz nada.
    if log_mensal.ultima_execucao.month == hoje.month and log_mensal.ultima_execucao.year == hoje.year:
        return

    # A tarefa precisa rodar para o mês anterior
    primeiro_dia_mes_atual = hoje.date().replace(day=1)
    ultimo_dia_mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
    primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)

    sucesso = _processar_e_salvar_ranking('mensal', primeiro_dia_mes_passado, ultimo_dia_mes_passado)
    if sucesso:
        log_mensal.ultima_execucao = hoje
        log_mensal.save()


def _processar_e_salvar_ranking(tipo, data_inicio, data_fim):
    """
    Lógica de cálculo e salvamento. Retorna True se bem-sucedido.
    (Esta é a mesma lógica do management command).
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
        return True # Sucesso, mas nada a fazer

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

