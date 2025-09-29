# gamificacao/models.py

from django.db import models
from django.contrib.auth.models import User
from usuarios.models import UserProfile
from django.utils import timezone
from datetime import date
from storages.backends.s3boto3 import S3Boto3Storage
from django.db.models import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from questoes.models import Disciplina, Assunto, Banca # Usado no contexto_json
from django.core.exceptions import ValidationError
from simulados.models import Simulado # Adicione esta importação no topo
from questoes.models import Disciplina, Assunto, Banca 
from django.db import transaction
from django.db.models import JSONField, Max
# =======================================================================
# MODELO DE CONFIGURAÇÕES GLOBAIS DA GAMIFICAÇÃO
# =======================================================================
class GamificationSettings(models.Model):
    """
    Singleton para armazenar todas as variáveis e regras de negócio da gamificação,
    permitindo que o administrador ajuste a economia do sistema sem alterar o código.
    """
    # --- SEÇÃO 1: XP POR QUESTÕES ---
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
    
    # --- SEÇÃO 2: BÔNUS E METAS ---
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

    # --- SEÇÃO 3: REGRAS DE SEGURANÇA E ANTI-FARMING ---
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
    
    # --- SEÇÃO 4: XP POR SIMULADOS ---
    usar_xp_dinamico_simulado = models.BooleanField(
        default=True, verbose_name="Usar XP Dinâmico por Desempenho em Simulados?",
        help_text="Se marcado, o XP será calculado com base nos acertos/erros. Se desmarcado, usará o valor fixo abaixo."
    )
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

    # --- SEÇÃO 5: MOEDAS VIRTUAIS ---
    moedas_por_acerto = models.PositiveIntegerField(
        default=5, verbose_name="Moedas por Acerto de Questão"
    )
    moedas_por_meta_diaria = models.PositiveIntegerField(
        default=25, verbose_name="Moedas Bônus por Meta Diária"
    )
    moedas_por_conclusao_simulado = models.PositiveIntegerField(
        default=50, verbose_name="Moedas por Concluir Simulado"
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

# =======================================================================
# MODELOS DE DADOS DO USUÁRIO
# =======================================================================
class ProfileGamificacao(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='gamificacao_data')
    level = models.IntegerField(default=1, verbose_name="Nível")
    xp = models.IntegerField(default=0, verbose_name="Pontos de Experiência (XP)")
    moedas = models.PositiveIntegerField(default=100, verbose_name="Fragmentos de Conhecimento (Moedas)")
    acertos_consecutivos = models.IntegerField(default=0, verbose_name="Acertos Consecutivos")
    bonus_xp_ativo = models.BooleanField(default=False, help_text="Indica se o bônus de XP em dobro está ativo.")
    cooldowns_ativos = JSONField(default=dict, blank=True, help_text="Armazena timestamps de cooldowns para evitar farming.")

    def __str__(self):
        return f"Nível {self.level} de {self.user_profile.user.username}"

class ProfileStreak(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='streak_data')
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    last_practice_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Streak de {self.user_profile.user.username}: {self.current_streak} dias"

    def update_streak(self):
        today = date.today()
        if self.last_practice_date == today: return
        if self.last_practice_date and (today - self.last_practice_date).days == 1:
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.last_practice_date = today
        if self.current_streak > self.max_streak:
            self.max_streak = self.current_streak
        self.save()

class MetaDiariaUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='metas_diarias')
    data = models.DateField(default=date.today)
    questoes_resolvidas = models.PositiveIntegerField(default=0)
    meta_atingida = models.BooleanField(default=False)
    xp_ganho_dia = models.PositiveIntegerField(default=0)
    class Meta: unique_together = ('user_profile', 'data'); ordering = ['-data']
    def __str__(self): status = "Atingida" if self.meta_atingida else "Em progresso"; return f"Meta de {self.user_profile.user.username} em {self.data.strftime('%d/%m/%Y')}: {status}"

# =======================================================================
# MODELOS DE RANKING
# =======================================================================
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
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    posicao = models.PositiveIntegerField()
    acertos_periodo = models.PositiveIntegerField(default=0)
    respostas_periodo = models.PositiveIntegerField(default=0)
    class Meta: abstract = True; ordering = ['posicao']

class RankingSemanal(BaseRankingPeriodico):
    ano = models.PositiveIntegerField()
    semana = models.PositiveIntegerField()
    class Meta(BaseRankingPeriodico.Meta): unique_together = ('user_profile', 'ano', 'semana'); verbose_name = "Ranking Semanal"; verbose_name_plural = "Rankings Semanais"
    def __str__(self): return f"#{self.posicao} - {self.user_profile.user.username} (Semana {self.semana}/{self.ano})"

class RankingMensal(BaseRankingPeriodico):
    ano = models.PositiveIntegerField()
    mes = models.PositiveIntegerField()
    class Meta(BaseRankingPeriodico.Meta): unique_together = ('user_profile', 'ano', 'mes'); verbose_name = "Ranking Mensal"; verbose_name_plural = "Rankings Mensais"
    def __str__(self): return f"#{self.posicao} - {self.user_profile.user.username} (Mês {self.mes}/{self.ano})"


# =======================================================================
# MODELOS DE RECOMPENSAS (ITENS COSMÉTICOS)
# =======================================================================
class TipoDesbloqueio(models.Model):
    CHAVE_CHOICES = [
        ('NIVEL', 'Por Nível'),
        ('CONQUISTA', 'Por Conquista'),
        ('EVENTO', 'Evento / Manual'),
        ('CAMPANHA', 'Campanha'),
        ('LOJA', 'Comprável na Loja'),
    ]
    nome = models.CharField(max_length=50, choices=CHAVE_CHOICES, unique=True)

    def __str__(self):
        return self.get_nome_display()

class Recompensa(models.Model):
    class Raridade(models.TextChoices):
        COMUM = 'COMUM', 'Comum'
        RARO = 'RARO', 'Raro'
        EPICO = 'EPICO', 'Épico'
        LENDARIO = 'LENDARIO', 'Lendário'
        MITICO = 'MITICO', 'Mítico'
    
    nome = models.CharField(max_length=100, verbose_name="Nome")
    descricao = models.CharField(max_length=255, help_text="Como desbloquear este item.", verbose_name="Descrição")
    imagem = models.ImageField(upload_to='gamificacao_recompensas/', storage=S3Boto3Storage(), null=True, blank=True, verbose_name="Imagem")
    
    tipos_desbloqueio = models.ManyToManyField(TipoDesbloqueio, blank=True, verbose_name="Formas de Desbloqueio")
    
    raridade = models.CharField(max_length=20, choices=Raridade.choices, default=Raridade.COMUM, verbose_name="Raridade")
    nivel_necessario = models.PositiveIntegerField(null=True, blank=True, verbose_name="Nível Necessário", help_text="Preencha se for desbloqueável por nível.")
    
    preco_moedas = models.PositiveIntegerField(null=True, blank=True, default=0, verbose_name="Preço em Moedas", help_text="Preencha se for comprável na loja.")
    
    class Meta: 
        abstract = True
        ordering = ['nome']
        
    def __str__(self): 
        return self.nome

    def clean(self):
        super().clean()
        if self.pk and not self.tipos_desbloqueio.exists():
            raise ValidationError({'tipos_desbloqueio': 'A recompensa deve ter pelo menos uma forma de desbloqueio.'})

        if self.pk:
            tipos_chaves = self.tipos_desbloqueio.values_list('nome', flat=True)
            if 'NIVEL' in tipos_chaves and not self.nivel_necessario:
                raise ValidationError({'nivel_necessario': 'Este campo é obrigatório para desbloqueio por nível.'})
            if 'LOJA' in tipos_chaves and (not self.preco_moedas or self.preco_moedas <= 0):
                raise ValidationError({'preco_moedas': 'O preço deve ser maior que zero para itens da loja.'})
            
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if not is_new:
             self.full_clean()

class Avatar(Recompensa): pass
class Borda(Recompensa): pass
class Banner(Recompensa): pass

# =======================================================================
# NOVA ARQUITETURA DE CONDIÇÕES (DATA-DRIVEN)
# =======================================================================

class VariavelDoJogo(models.Model):
    """
    Define as estatísticas do jogador que podem ser usadas para criar condições.
    Ex: "Total de Acertos", "Recorde de Streak", "Nível Atual".
    """
    nome_exibicao = models.CharField(max_length=100, verbose_name="Nome para o Admin", help_text="Ex: Total de Acertos, Recorde de Streak")
    chave = models.CharField(max_length=50, unique=True, help_text="Chave interna usada pelo sistema. Ex: 'total_acertos'")
    descricao = models.TextField(help_text="Explicação de como esta variável é calculada.")

    class Meta:
        verbose_name = "Variável do Jogo"
        verbose_name_plural = "Variáveis do Jogo"
        ordering = ['nome_exibicao']

    def __str__(self):
        return self.nome_exibicao

class Condicao(models.Model):
    """
    Modelo genérico que representa UMA condição para uma conquista.
    Ex: (Variável: 'total_acertos') (Operador: '>=') (Valor: 100)
    """
    class Operador(models.TextChoices):
        MAIOR_IGUAL = '>=', 'Maior ou igual a'
        MENOR_IGUAL = '<=', 'Menor ou igual a'
        IGUAL = '==', 'Igual a'
        DIFERENTE = '!=', 'Diferente de'

    conquista = models.ForeignKey('Conquista', on_delete=models.CASCADE, related_name="condicoes")
    variavel = models.ForeignKey(VariavelDoJogo, on_delete=models.SET_NULL, null=True, verbose_name="Variável a ser verificada")
    operador = models.CharField(max_length=4, choices=Operador.choices, default=Operador.MAIOR_IGUAL)
    valor = models.IntegerField(verbose_name="Valor para comparar", default=0)
    
    contexto_json = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name="Filtros Adicionais (JSON)", 
        help_text="Opcional. Use para filtrar variáveis. Ex: {'disciplina_id': 5}"
    )

    class Meta:
        verbose_name = "Condição"
        verbose_name_plural = "Condições"

    def __str__(self):
        if self.variavel:
            return f"Se '{self.variavel.nome_exibicao}' for '{self.get_operador_display()}' '{self.valor}'"
        return "Condição Inválida (sem variável)"


# =======================================================================
# MODELOS DE TRILHAS E CONQUISTAS (AJUSTADOS)
# =======================================================================
class TrilhaDeConquistas(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(help_text="Descreva o objetivo geral desta trilha de conquistas.")
    icone = models.CharField(max_length=50, help_text="Ex: 'fas fa-graduation-cap' (classe do Font Awesome)")
    ordem = models.PositiveIntegerField(
        default=0, 
        unique=True, 
        verbose_name="Ordem de Exibição",
        help_text="Define a ordem de exibição das trilhas (menor primeiro). Cada trilha deve ter uma ordem única."
    )

    class Meta: 
        ordering = ['ordem', 'nome']
        verbose_name = "Trilha de Conquistas"
        verbose_name_plural = "Trilhas de Conquistas"
    def __str__(self): 
        return self.nome

class SerieDeConquistas(models.Model):
    """
    Agrupamento para conquistas que seguem uma progressão linear (Ex: Bronze, Prata, Ouro).
    """
    nome = models.CharField(max_length=150, unique=True, verbose_name="Nome da Série")
    trilha = models.ForeignKey('TrilhaDeConquistas', on_delete=models.CASCADE, related_name='series')
    descricao = models.TextField(blank=True, verbose_name="Descrição da Série")
    ordem = models.PositiveIntegerField(default=0, help_text="Define a ordem de exibição das séries dentro da trilha.")

    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = "Série de Conquistas"
        verbose_name_plural = "Séries de Conquistas"

    def __str__(self):
        return self.nome

class Conquista(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(help_text="Explique o que o usuário precisa fazer para ganhar esta conquista.")
    icone = models.CharField(max_length=50, help_text="Ex: 'fas fa-fire' (classes do Font Awesome)")
    cor = models.CharField(max_length=20, default='gold', help_text="Cor do ícone (ex: 'gold', '#FFD700')")
    
    trilha = models.ForeignKey('TrilhaDeConquistas', on_delete=models.CASCADE, related_name='conquistas', null=True, blank=True)
    
    is_secreta = models.BooleanField(default=False, verbose_name="É uma Conquista Secreta?", help_text="Se marcado, não aparecerá na trilha até ser desbloqueada.")
    
    serie = models.ForeignKey(SerieDeConquistas, on_delete=models.PROTECT, null=True, blank=True, related_name='conquistas', verbose_name="Série")
    ordem_na_serie = models.PositiveIntegerField(default=0, db_index=True)
    sequencia_automatica = models.BooleanField(default=False, editable=False)

    pre_requisitos = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='desbloqueia', verbose_name="Pré-requisitos")
    recompensas = JSONField(default=dict, blank=True, verbose_name="Recompensas Diretas", help_text="JSON com as recompensas concedidas. Ex: {\"xp\": 100, \"moedas\": 50, \"avatares\": [1, 2]}")
    
    class Meta: 
        ordering = ['trilha__ordem', 'serie__ordem', 'ordem_na_serie', 'nome']
        
    def __str__(self): 
        return self.nome
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Garante a ordem correta na criação
        if is_new and self.serie:
            maior_ordem = self.serie.conquistas.aggregate(max_ordem=Max('ordem_na_serie'))['max_ordem'] or 0
            self.ordem_na_serie = maior_ordem + 1
        
        super().save(*args, **kwargs)

        # Atualiza o pré-requisito sequencial
        if self.serie and self.ordem_na_serie > 1:
            try:
                conquista_anterior = Conquista.objects.get(serie=self.serie, ordem_na_serie=self.ordem_na_serie - 1)
                if not self.pre_requisitos.filter(pk=conquista_anterior.pk).exists():
                    self.pre_requisitos.set([conquista_anterior])
            except Conquista.DoesNotExist:
                self.pre_requisitos.clear()
        
        # =======================================================================
        # INÍCIO DA LÓGICA DE SINCRONIZAÇÃO DE CONDIÇÕES (PUSH)
        # =======================================================================
        # Se a conquista que está sendo salva é a PRIMEIRA da série, ela dita as regras.
        if self.serie and self.ordem_na_serie == 1:
            # Pega as condições "mestras" (as que acabaram de ser salvas no formulário)
            master_conditions = list(self.condicoes.all())
            
            # Busca todas as outras conquistas na mesma série para atualizá-las
            achievements_to_update = Conquista.objects.filter(
                serie=self.serie, 
                ordem_na_serie__gt=1
            ).prefetch_related('condicoes', 'condicoes__variavel')

            for achievement in achievements_to_update:
                # 1. Guarda os valores atuais para não perdermos a progressão
                current_values = {
                    c.variavel.chave: c.valor 
                    for c in achievement.condicoes.all() if c.variavel
                }
                
                # 2. Limpa as condições antigas
                achievement.condicoes.all().delete()
                
                # 3. Recria as condições com base no "molde" da primeira conquista
                new_conditions = []
                for master_cond in master_conditions:
                    # Usa o valor antigo se existir, senão usa o valor da primeira
                    valor_preservado = current_values.get(master_cond.variavel.chave, master_cond.valor)
                    
                    new_conditions.append(Condicao(
                        conquista=achievement,
                        variavel=master_cond.variavel,
                        operador=master_cond.operador,
                        contexto_json=master_cond.contexto_json,
                        valor=valor_preservado
                    ))
                
                # 4. Cria as novas condições em lote
                if new_conditions:
                    Condicao.objects.bulk_create(new_conditions)
        # =======================================================================
        # FIM DA LÓGICA DE SINCRONIZAÇÃO
        # =======================================================================

    @transaction.atomic
    def delete(self, *args, **kwargs):
        dependentes = Conquista.objects.filter(pre_requisitos=self)
        if dependentes.exists():
            nomes_dependentes = ", ".join([f"'{c.nome}'" for c in dependentes])
            raise ValidationError(f"Não é possível excluir. A(s) conquista(s) {nomes_dependentes} depende(m) desta.")

        serie_a_reordenar = self.serie
        ordem_excluida = self.ordem_na_serie
        
        super().delete(*args, **kwargs)
        
        if serie_a_reordenar and ordem_excluida > 0:
            conquistas_posteriores = Conquista.objects.filter(
                serie=serie_a_reordenar, 
                ordem_na_serie__gt=ordem_excluida
            ).order_by('ordem_na_serie')
            
            for i, conquista in enumerate(conquistas_posteriores):
                nova_ordem = ordem_excluida + i
                conquista.ordem_na_serie = nova_ordem
                conquista.save(update_fields=['ordem_na_serie'])
class ConquistaUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='conquistas_usuario')
    conquista = models.ForeignKey(Conquista, on_delete=models.CASCADE)
    data_conquista = models.DateTimeField(auto_now_add=True)
    class Meta: 
        unique_together = ('user_profile', 'conquista')
        ordering = ['-data_conquista']
    def __str__(self): 
        return f"{self.user_profile.user.username} desbloqueou {self.conquista.nome}"


# =======================================================================
# MODELOS DE CAMPANHAS E EVENTOS
# =======================================================================
class Campanha(models.Model):
    class Gatilho(models.TextChoices):
        COMPLETAR_SIMULADO = 'COMPLETAR_SIMULADO', 'Ao Completar um Simulado'
        RANKING_SEMANAL_CONCLUIDO = 'RANKING_SEMANAL_CONCLUIDO', 'Ao Fechar o Ranking Semanal'
        RANKING_MENSAL_CONCLUIDO = 'RANKING_MENSAL_CONCLUIDO', 'Ao Fechar o Ranking Mensal'
        PRIMEIRA_ACAO_DO_DIA = 'PRIMEIRA_ACAO_DO_DIA', 'Na Primeira Ação do Dia'
        META_DIARIA_CONCLUIDA = 'META_DIARIA_CONCLUIDA', 'Ao Concluir a Meta Diária'
        CONQUISTA_DESBLOQUEADA = 'CONQUISTA_DESBLOQUEADA', 'Ao Desbloquear uma Conquista'
        COMENTARIO_PUBLICADO = 'COMENTARIO_PUBLICADO', 'Ao Publicar um Comentário'
        LIKE_EM_COMENTARIO_CONCEDIDO = 'LIKE_EM_COMENTARIO_CONCEDIDO', 'Ao Curtir um Comentário'


    class TipoRecorrencia(models.TextChoices):
        UNICA = 'UNICA', 'Apenas Uma Vez (Geral)'
        UNICA_POR_USUARIO = 'UNICA_POR_USUARIO', 'Apenas Uma Vez por Usuário'
        DIARIA = 'DIARIA', 'Diariamente'
        SEMANAL = 'SEMANAL', 'Semanalmente'
        MENSAL = 'MENSAL', 'Mensalmente'

    nome = models.CharField(max_length=255, verbose_name="Nome da Campanha")
    ativo = models.BooleanField(default=True, verbose_name="Campanha Ativa?")
    data_inicio = models.DateTimeField(default=timezone.now, verbose_name="Início da Vigência")
    data_fim = models.DateTimeField(null=True, blank=True, verbose_name="Fim da Vigência (opcional)")
    tipo_recorrencia = models.CharField(max_length=20, choices=TipoRecorrencia.choices, default=TipoRecorrencia.SEMANAL)
    gatilho = models.CharField(max_length=50, choices=Gatilho.choices, verbose_name="Gatilho de Ativação")
    
    simulado_especifico = models.ForeignKey(
        Simulado, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Simulado Específico (Opcional)",
        help_text="Se um simulado for selecionado, esta campanha só será ativada pela conclusão dele."
    )
    grupos_de_condicoes = JSONField(default=list, blank=True, verbose_name="Grupos de Condições e Recompensas")
    
    def __str__(self): return self.nome

# =======================================================================
# NOVO MODELO PARA O GAP "O PRIMEIRO DO DIA"
# =======================================================================
class ConquistaDiariaGlobalLog(models.Model):
    TIPO_CHOICES = [
        ('META_DIARIA', 'Primeiro a Concluir a Meta Diária'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.DateField()
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    conquistado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('data', 'tipo') # Garante que só haja um registro por dia/tipo

class CampanhaUsuarioCompletion(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    campanha = models.ForeignKey(Campanha, on_delete=models.CASCADE)
    ciclo_id = models.CharField(max_length=20, help_text="Identificador do ciclo. Ex: '2024-W38' (semanal) ou '2024-09' (mensal)")
    data_conclusao = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ('user_profile', 'campanha', 'ciclo_id'); ordering = ['-data_conclusao']
    def __str__(self): return f"{self.user_profile.user.username} completou {self.campanha.nome} no ciclo {self.ciclo_id}"

# =======================================================================
# MODELOS DE CONTROLE E LOG DE RECOMPENSAS
# =======================================================================
class RecompensaUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='recompensas_ganhas')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    recompensa = GenericForeignKey('content_type', 'object_id')
    data_concessao = models.DateTimeField(auto_now_add=True)
    origem_campanha = models.ForeignKey(Campanha, on_delete=models.SET_NULL, null=True, blank=True, help_text="Campanha que concedeu o prêmio.")
    concedido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Admin que concedeu manualmente.")
    
    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]
        ordering = ['-data_concessao']

    def __str__(self):
        recompensa_nome = "Item Excluído"
        if self.recompensa:
            recompensa_nome = self.recompensa.nome
        return f"{self.user_profile.user.username} ganhou {recompensa_nome}"

class RecompensaPendente(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='recompensas_pendentes'); content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE); object_id = models.PositiveIntegerField(); recompensa = GenericForeignKey('content_type', 'object_id'); data_ganho = models.DateTimeField(auto_now_add=True); resgatado_em = models.DateTimeField(null=True, blank=True); origem_desbloqueio = models.CharField(max_length=255, help_text="Descrição da origem do prêmio. Ex: 'Alcançou o Nível 10', 'Conquista Mestre Cuca'")
    class Meta: ordering = ['-data_ganho']; verbose_name = "Recompensa Pendente"; verbose_name_plural = "Recompensas Pendentes"; unique_together = ('user_profile', 'content_type', 'object_id')
    def __str__(self): status = "Resgatado" if self.resgatado_em else "Pendente"; return f"Prêmio para {self.user_profile.user.username} - Status: {status}"
    def resgatar(self):
        if self.resgatado_em: return False
        if isinstance(self.recompensa, Avatar): AvatarUsuario.objects.get_or_create(user_profile=self.user_profile, avatar=self.recompensa)
        elif isinstance(self.recompensa, Borda): BordaUsuario.objects.get_or_create(user_profile=self.user_profile, borda=self.recompensa)
        elif isinstance(self.recompensa, Banner): BannerUsuario.objects.get_or_create(user_profile=self.user_profile, banner=self.recompensa)
        else: return False
        self.resgatado_em = timezone.now(); self.save(update_fields=['resgatado_em']); return True

class AvatarUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='avatares_desbloqueados'); avatar = models.ForeignKey(Avatar, on_delete=models.CASCADE); data_desbloqueio = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ('user_profile', 'avatar')

class BordaUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='bordas_desbloqueadas'); borda = models.ForeignKey(Borda, on_delete=models.CASCADE); data_desbloqueio = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ('user_profile', 'borda')

class BannerUsuario(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='banners_desbloqueados'); banner = models.ForeignKey(Banner, on_delete=models.CASCADE); data_desbloqueio = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ('user_profile', 'banner')