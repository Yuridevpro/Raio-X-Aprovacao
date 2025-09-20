# gamificacao/models.py

from django.db import models
from django.contrib.auth.models import User
from usuarios.models import UserProfile
from django.utils import timezone
from datetime import date
from storages.backends.s3boto3 import S3Boto3Storage
# Imports necessários para o novo sistema
from django.db.models import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


# gamificacao/models.py (classe GamificationSettings e ProfileGamificacao completas)

class GamificationSettings(models.Model):
    # ... (Seções 1 e 2 sem alterações) ...
    xp_por_acerto = models.PositiveIntegerField(
        default=10, verbose_name="XP por Acerto Padrão",
        help_text="XP ganho ao acertar uma questão que já foi respondida corretamente antes."
    )
    xp_por_erro = models.PositiveIntegerField(
        default=2, verbose_name="XP por Erro",
        help_text="XP ganho (ou 'de consolação') ao errar uma questão."
    )
    xp_acerto_primeira_vez = models.PositiveIntegerField(
        default=15, verbose_name="Bônus de XP por Acerto na Primeira Vez",
        help_text="XP total ganho ao acertar uma questão pela primeira vez. Deve ser maior que o acerto padrão."
    )
    xp_acerto_redencao = models.PositiveIntegerField(
        default=20, verbose_name="Bônus de XP por Redenção (Corrigir um Erro)",
        help_text="XP total ganho ao acertar uma questão que o usuário errou anteriormente. Recompensa o estudo e a correção."
    )
    acertos_consecutivos_para_bonus = models.PositiveIntegerField(
        default=5, verbose_name="Nº de Acertos Consecutivos para Bônus",
        help_text="Quantas questões o usuário precisa acertar em sequência para ativar o multiplicador de XP."
    )
    bonus_multiplicador_acertos_consecutivos = models.FloatField(
        default=2.0, verbose_name="Multiplicador de XP do Bônus",
        help_text="Por quanto o XP de acerto será multiplicado quando o bônus estiver ativo (Ex: 2.0 para XP em dobro)."
    )
    xp_bonus_meta_diaria = models.PositiveIntegerField(
        default=50, verbose_name="Bônus de XP por Meta Diária",
        help_text="Bônus de XP concedido uma vez por dia ao atingir a meta de questões resolvidas."
    )
    meta_diaria_questoes = models.PositiveIntegerField(
        default=15, verbose_name="Questões para Atingir a Meta Diária",
        help_text="Número de questões que o usuário precisa resolver no dia para ganhar o bônus."
    )

    # =======================================================================
    # SEÇÃO 3: REGRAS DE SEGURANÇA E ANTI-FARMING (sem alterações nesta etapa)
    # =======================================================================
    habilitar_teto_xp_diario = models.BooleanField(
        default=False,
        verbose_name="Habilitar Teto de XP Diário?",
        help_text="Se marcado, limita a quantidade de XP que um usuário pode ganhar por dia."
    )
    teto_xp_diario = models.PositiveIntegerField(
        default=500, verbose_name="Teto de XP Diário",
        help_text="Quantidade máxima de XP que pode ser ganha em 24 horas, se o teto estiver habilitado."
    )
    cooldown_mesma_questao_horas = models.PositiveIntegerField(
        default=24, verbose_name="Cooldown para ganhar XP na mesma questão (em horas)",
        help_text="Impede que o usuário ganhe XP respondendo à mesma questão várias vezes em um curto período."
    )
    tempo_minimo_entre_respostas_segundos = models.PositiveIntegerField(
        default=5, verbose_name="Tempo mínimo entre respostas para ganhar XP (em segundos)",
        help_text="Proteção anti-bot. Respostas mais rápidas que isso não geram XP."
    )
    cooldown_mesmo_simulado_horas = models.PositiveIntegerField(
        default=48, verbose_name="Cooldown para ganhar XP no mesmo simulado (em horas)",
        help_text="Impede que o usuário ganhe XP finalizando o mesmo simulado várias vezes em um curto período."
    )
    
    # =======================================================================
    # SEÇÃO 4: XP POR SIMULADOS E RANKINGS (COM ADIÇÕES)
    # =======================================================================
    usar_xp_dinamico_simulado = models.BooleanField(
        default=True, verbose_name="Usar XP Dinâmico por Desempenho em Simulados?",
        help_text="Se marcado, o XP será calculado com base nos acertos/erros. Se desmarcado, usará o valor fixo abaixo."
    )
    # >>> NOVO CAMPO PARA GERENCIAR A FÓRMULA <<<
    xp_dinamico_considera_erros = models.BooleanField(
        default=True, verbose_name="Considerar XP por Erro no cálculo dinâmico?",
        help_text="Se marcado, a pontuação dos erros será somada no cálculo do XP dinâmico."
    )
    multiplicador_xp_simulado = models.FloatField(
        default=1.2, verbose_name="Multiplicador de XP para Simulados Dinâmicos",
        help_text="Ex: 1.2 significa que o XP ganho no simulado será 20% maior que na prática normal."
    )
    xp_base_simulado_concluido = models.PositiveIntegerField(
        default=100, verbose_name="XP Fixo por Simulado Concluído",
        help_text="XP ganho apenas por finalizar um simulado, se o XP dinâmico estiver desativado."
    )
    bonus_xp_ranking_semanal = models.PositiveIntegerField(
        default=250, verbose_name="Bônus de XP para Top 3 Semanal",
        help_text="XP extra concedido aos 3 primeiros do ranking semanal."
    )
    bonus_xp_ranking_mensal = models.PositiveIntegerField(
        default=500, verbose_name="Bônus de XP para Top 3 Mensal",
        help_text="XP extra concedido aos 3 primeiros do ranking mensal."
    )
    bonus_consecutivo_ranking = models.PositiveIntegerField(
        default=100, verbose_name="Bônus de XP por Top 3 Consecutivo",
        help_text="XP adicional se o usuário ficou no Top 3 na semana/mês anterior também."
    )

    def __str__(self):
        return "Configurações de Gamificação"

    class Meta:
        verbose_name = "Configurações de Gamificação"
        verbose_name_plural = "Configurações de Gamificação"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(GamificationSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class ProfileGamificacao(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='gamificacao_data')
    level = models.IntegerField(default=1, verbose_name="Nível")
    xp = models.IntegerField(default=0, verbose_name="Pontos de Experiência (XP)")
    acertos_consecutivos = models.IntegerField(default=0, verbose_name="Acertos Consecutivos")
    bonus_xp_ativo = models.BooleanField(default=False, help_text="Indica se o bônus de XP em dobro está ativo.")
    
    # >>> NOVO CAMPO PARA COOLDOWNS SEGUROS <<<
    cooldowns_ativos = JSONField(default=dict, blank=True, help_text="Armazena timestamps de cooldowns para evitar farming.")

    def __str__(self):
        return f"Nível {self.level} de {self.user_profile.user.username}"


class TarefaAgendadaLog(models.Model):
    TAREFA_CHOICES = [
        ('gerar_ranking_semanal', 'Gerar Ranking Semanal'),
        ('gerar_ranking_mensal', 'Gerar Ranking Mensal'),
    ]
    nome_tarefa = models.CharField(max_length=50, choices=TAREFA_CHOICES, unique=True)
    ultima_execucao = models.DateTimeField()

    def __str__(self):
        return f"Última execução de '{self.get_nome_tarefa_display()}' em {self.ultima_execucao}"

class BaseRankingPeriodico(models.Model):
    """Modelo abstrato para evitar repetição de código nos rankings."""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    posicao = models.PositiveIntegerField()
    acertos_periodo = models.PositiveIntegerField(default=0)
    respostas_periodo = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ['posicao']

class RankingSemanal(BaseRankingPeriodico):
    ano = models.PositiveIntegerField()
    semana = models.PositiveIntegerField()

    class Meta(BaseRankingPeriodico.Meta):
        unique_together = ('user_profile', 'ano', 'semana')
        verbose_name = "Ranking Semanal"
        verbose_name_plural = "Rankings Semanais"

    def __str__(self):
        return f"#{self.posicao} - {self.user_profile.user.username} (Semana {self.semana}/{self.ano})"

class RankingMensal(BaseRankingPeriodico):
    ano = models.PositiveIntegerField()
    mes = models.PositiveIntegerField()

    class Meta(BaseRankingPeriodico.Meta):
        unique_together = ('user_profile', 'ano', 'mes')
        verbose_name = "Ranking Mensal"
        verbose_name_plural = "Rankings Mensais"

    def __str__(self):
        return f"#{self.posicao} - {self.user_profile.user.username} (Mês {self.mes}/{self.ano})"

class MetaDiariaUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='metas_diarias')
    data = models.DateField(default=date.today)
    questoes_resolvidas = models.PositiveIntegerField(default=0)
    meta_atingida = models.BooleanField(default=False)
    xp_ganho_dia = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user_profile', 'data')
        ordering = ['-data']

    def __str__(self):
        status = "Atingida" if self.meta_atingida else "Em progresso"
        return f"Meta de {self.user_profile.user.username} em {self.data.strftime('%d/%m/%Y')}: {status}"



class ProfileStreak(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='streak_data')
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    last_practice_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Streak de {self.user_profile.user.username}: {self.current_streak} dias"

    def update_streak(self):
        today = date.today()
        if self.last_practice_date == today:
            return
        if self.last_practice_date and (today - self.last_practice_date).days == 1:
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.last_practice_date = today
        if self.current_streak > self.max_streak:
            self.max_streak = self.current_streak
        self.save()

class Conquista(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    icone = models.CharField(max_length=50, help_text="Ex: 'fas fa-fire' (classes do Font Awesome)")
    cor = models.CharField(max_length=20, default='gold', help_text="Cor do ícone (ex: 'gold', '#FFD700')")
    chave = models.CharField(max_length=50, unique=True, help_text="Identificador único, ex: 'STREAK_7_DIAS'")

    def __str__(self):
        return self.nome

class ConquistaUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='conquistas')
    conquista = models.ForeignKey(Conquista, on_delete=models.CASCADE)
    data_conquista = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_profile', 'conquista')

    def __str__(self):
        return f"{self.user_profile.user.username} desbloqueou {self.conquista.nome}"

class Recompensa(models.Model):
    """Modelo abstrato para itens cosméticos e outros prêmios."""
    class TipoDesbloqueio(models.TextChoices):
        NIVEL = 'NIVEL', 'Por Nível'
        CONQUISTA = 'CONQUISTA', 'Por Conquista'
        EVENTO = 'EVENTO', 'Evento Especial'
        REGRA = 'REGRA', 'Regra Automática' # Novo tipo para o sistema de regras

    class Raridade(models.TextChoices):
        COMUM = 'COMUM', 'Comum'
        RARO = 'RARO', 'Raro'
        EPICO = 'EPICO', 'Épico'
        LENDARIO = 'LENDARIO', 'Lendário'
        MITICO = 'MITICO', 'Mítico'
    
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, help_text="Como desbloquear este item.")
    imagem = models.ImageField(upload_to='gamificacao_recompensas/', storage=S3Boto3Storage(), null=True, blank=True)
    
    tipo_desbloqueio = models.CharField(max_length=20, choices=TipoDesbloqueio.choices)
    raridade = models.CharField(max_length=20, choices=Raridade.choices, default=Raridade.COMUM)

    nivel_necessario = models.PositiveIntegerField(null=True, blank=True)
    conquista_necessaria = models.ForeignKey('Conquista', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Avatar(Recompensa):
    pass

class Borda(Recompensa):
    pass

class Banner(Recompensa):
    pass

# NOVO MODELO DE REGRA DE RECOMPENSA
class RegraRecompensa(models.Model):
    class Gatilho(models.TextChoices):
        COMPLETAR_SIMULADO = 'COMPLETAR_SIMULADO', 'Completar um Simulado'
        RANKING_SEMANAL_TOP_N = 'RANKING_SEMANAL_TOP_N', 'Ficar no Top N do Ranking Semanal'
        RANKING_MENSAL_TOP_N = 'RANKING_MENSAL_TOP_N', 'Ficar no Top N do Ranking Mensal'

    nome = models.CharField(max_length=255, verbose_name="Nome da Regra")
    ativo = models.BooleanField(default=True, verbose_name="Regra Ativa?")
    gatilho = models.CharField(max_length=50, choices=Gatilho.choices, verbose_name="Gatilho de Ativação")
    
    condicoes = JSONField(default=dict, blank=True, help_text="Ex: {\"top_n\": 3} ou {\"min_acertos_percent\": 80}")
    
    avatares = models.ManyToManyField(Avatar, blank=True, verbose_name="Avatares como Recompensa")
    bordas = models.ManyToManyField(Borda, blank=True, verbose_name="Bordas como Recompensa")
    banners = models.ManyToManyField(Banner, blank=True, verbose_name="Banners como Recompensa")
    xp_extra = models.PositiveIntegerField(default=0, help_text="XP adicional concedido ao cumprir esta regra.")

    def __str__(self):
        return self.nome

# NOVO MODELO PARA LOG/AUDITORIA DE RECOMPENSAS
class RecompensaUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='recompensas_ganhas')
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    recompensa = GenericForeignKey('content_type', 'object_id')
    
    data_concessao = models.DateTimeField(auto_now_add=True)
    origem = models.ForeignKey(RegraRecompensa, on_delete=models.SET_NULL, null=True, blank=True, help_text="Regra que concedeu o prêmio.")
    concedido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Admin que concedeu manualmente.")
    
    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]
        ordering = ['-data_concessao']

    def __str__(self):
        recompensa_nome = "Item Excluído"
        if self.recompensa:
            recompensa_nome = self.recompensa.nome
        return f"{self.user_profile.user.username} ganhou {recompensa_nome}"

class AvatarUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='avatares_desbloqueados')
    avatar = models.ForeignKey(Avatar, on_delete=models.CASCADE)
    data_desbloqueio = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_profile', 'avatar')

class BordaUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='bordas_desbloqueadas')
    borda = models.ForeignKey(Borda, on_delete=models.CASCADE)
    data_desbloqueio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user_profile', 'borda')

class BannerUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='banners_desbloqueados')
    banner = models.ForeignKey(Banner, on_delete=models.CASCADE)
    data_desbloqueio = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_profile', 'banner')