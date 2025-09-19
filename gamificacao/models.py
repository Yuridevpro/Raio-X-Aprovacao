# gamificacao/models.py

from django.db import models
from django.contrib.auth.models import User
from usuarios.models import UserProfile
from django.utils import timezone
from datetime import date
from storages.backends.s3boto3 import S3Boto3Storage


# = a. NOVO MODELO PARA CONFIGURAÇÕES DE XP
class GamificationSettings(models.Model):
    """
    Singleton model to store global gamification settings,
    editable in the Django admin panel.
    """
    xp_por_acerto = models.PositiveIntegerField(default=10, help_text="XP ganho por cada questão respondida corretamente.")
    xp_por_erro = models.PositiveIntegerField(default=1, help_text="XP ganho por cada questão respondida incorretamente.")
    xp_bonus_meta_diaria = models.PositiveIntegerField(default=50, help_text="Bônus de XP por completar a meta diária.")
    meta_diaria_questoes = models.PositiveIntegerField(default=15, help_text="Número de questões para atingir a meta diária.")
    acertos_consecutivos_para_bonus = models.PositiveIntegerField(default=5, help_text="Número de acertos consecutivos para ativar o bônus de XP em dobro.")
    
    def __str__(self):
        return "Configurações de Gamificação"

    class Meta:
        verbose_name = "Configurações de Gamificação"
        verbose_name_plural = "Configurações de Gamificação"

    def save(self, *args, **kwargs):
        # Garante que haverá apenas uma instância deste modelo
        self.pk = 1
        super(GamificationSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        # Método para carregar a única instância de configurações
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


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


# =======================================================================
# NOVO MODELO PARA ARMAZENAR DADOS DE XP E NÍVEL
# =======================================================================
class MetaDiariaUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='metas_diarias')
    data = models.DateField(default=date.today)
    questoes_resolvidas = models.PositiveIntegerField(default=0)
    meta_atingida = models.BooleanField(default=False)
    xp_ganho_dia = models.PositiveIntegerField(default=0) # <-- NOVO CAMPO

    class Meta:
        # Garante que haverá apenas um registro por usuário por dia.
        unique_together = ('user_profile', 'data')
        ordering = ['-data']

    def __str__(self):
        status = "Atingida" if self.meta_atingida else "Em progresso"
        return f"Meta de {self.user_profile.user.username} em {self.data.strftime('%d/%m/%Y')}: {status}"

class ProfileGamificacao(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='gamificacao_data')
    level = models.IntegerField(default=1, verbose_name="Nível")
    xp = models.IntegerField(default=0, verbose_name="Pontos de Experiência (XP)")
    acertos_consecutivos = models.IntegerField(default=0, verbose_name="Acertos Consecutivos")
    # b. NOVO CAMPO PARA BÔNUS DE XP
    bonus_xp_ativo = models.BooleanField(default=False, help_text="Indica se o bônus de XP em dobro está ativo.")

    def __str__(self):
        return f"Nível {self.level} de {self.user_profile.user.username}"


class ProfileStreak(models.Model):
    """ Armazena os dados de sequência (streak) de um usuário. """
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
    """ Define uma conquista que pode ser desbloqueada. """
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    icone = models.CharField(max_length=50, help_text="Ex: 'fas fa-fire' (classes do Font Awesome)")
    cor = models.CharField(max_length=20, default='gold', help_text="Cor do ícone (ex: 'gold', '#FFD700')")
    chave = models.CharField(max_length=50, unique=True, help_text="Identificador único, ex: 'STREAK_7_DIAS'")

    def __str__(self):
        return self.nome

class ConquistaUsuario(models.Model):
    """ Liga um usuário a uma conquista desbloqueada. """
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='conquistas')
    conquista = models.ForeignKey(Conquista, on_delete=models.CASCADE)
    data_conquista = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_profile', 'conquista')

    def __str__(self):
        return f"{self.user_profile.user.username} desbloqueou {self.conquista.nome}"


class Recompensa(models.Model):
    """Modelo abstrato para itens cosméticos."""
    class TipoDesbloqueio(models.TextChoices):
        NIVEL = 'NIVEL', 'Por Nível'
        CONQUISTA = 'CONQUISTA', 'Por Conquista'
        EVENTO = 'EVENTO', 'Evento Especial'

    # c. CAMPO DE RARIDADE ADICIONADO
    class Raridade(models.TextChoices):
        COMUM = 'COMUM', 'Comum'
        RARO = 'RARO', 'Raro'
        EPICO = 'EPICO', 'Épico'
        LENDARIO = 'LENDARIO', 'Lendário'
        MITICO = 'MITICO', 'Mítico'
    
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, help_text="Como desbloquear este item.")
    imagem = models.ImageField(upload_to='gamificacao_recompensas/', storage=S3Boto3Storage())
    
    tipo_desbloqueio = models.CharField(max_length=20, choices=TipoDesbloqueio.choices)
    raridade = models.CharField(max_length=20, choices=Raridade.choices, default=Raridade.COMUM)

    # Requisitos para desbloqueio
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

# gamificacao/models.py

class Banner(Recompensa):
    background_position = models.CharField(
        max_length=50, 
        default='50% 50%', 
        help_text="Define o ponto focal da imagem (ex: '50% 50%')."
    )
    # NOVO CAMPO PARA O ZOOM
    background_size = models.CharField(
        max_length=50,
        default='cover',
        help_text="Define o nível de zoom da imagem (ex: '120%')."
    )

class BannerUsuario(models.Model):
    """ Tabela que liga os banners desbloqueados a cada usuário. """
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='banners_desbloqueados')
    banner = models.ForeignKey(Banner, on_delete=models.CASCADE)
    data_desbloqueio = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_profile', 'banner')

class AvatarUsuario(models.Model):
    """ Tabela que liga os avatares desbloqueados a cada usuário. """
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='avatares_desbloqueados')
    avatar = models.ForeignKey(Avatar, on_delete=models.CASCADE)
    data_desbloqueio = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_profile', 'avatar')

class BordaUsuario(models.Model):
    """ Tabela que liga as bordas desbloqueadas a cada usuário. """
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='bordas_desbloqueadas')
    borda = models.ForeignKey(Borda, on_delete=models.CASCADE)
    data_desbloqueio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user_profile', 'borda')