# pratica/models.py

from django.db import models
from django.contrib.auth.models import User
from questoes.models import Questao
from django.db.models import Q

# =======================================================================
# MODELOS DE DADOS DE INTERAÇÃO DO USUÁRIO (SEM ALTERAÇÕES)
# =======================================================================

class RespostaUsuario(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE)
    alternativa_selecionada = models.CharField(max_length=1)
    foi_correta = models.BooleanField()
    data_resposta = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('usuario', 'questao')
    def __str__(self):
        status = "Correta" if self.foi_correta else "Incorreta"
        return f"{self.usuario.username} - Questão {self.questao.id} - {status}"

class Comentario(models.Model):
    questao = models.ForeignKey(Questao, related_name='comentarios', on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    conteudo = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='comentarios_curtidos', blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='respostas')
    class Meta:
        ordering = ['data_criacao']
    def __str__(self):
        return f'Comentário de {self.usuario.username} na questão {self.questao.id}'
    
class FiltroSalvo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    parametros_url = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('usuario', 'nome')
        ordering = ['-data_criacao']
    def __str__(self):
        return f'Filtro "{self.nome}" de {self.usuario.username}'


# =======================================================================
# MODELO DE NOTIFICAÇÃO (VERSÃO FINAL E SIMPLIFICADA)
# =======================================================================

class Notificacao(models.Model):
    class TipoErro(models.TextChoices):
        ENUNCIADO_ALTERNATIVA = 'ENUNCIADO_ALTERNATIVA', 'Enunciado/alternativa errada'
        DISCIPLINA_ASSUNTO = 'DISCIPLINA_ASSUNTO', 'Disciplina ou assunto errado'
        QUESTAO_ANULADA = 'QUESTAO_ANULADA', 'Questão anulada'
        QUESTAO_DESATUALIZADA = 'QUESTAO_DESATUALIZADA', 'Questão desatualizada'
        QUESTAO_DUPLICADA = 'QUESTAO_DUPLICADA', 'Questão duplicada'

    # --- FLUXO DE STATUS FINAL E SIMPLES ---
    # Removemos 'EM_ANALISE' e 'ARQUIVADO' para um fluxo de trabalho mais direto.
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        RESOLVIDO = 'RESOLVIDO', 'Corrigido'
        REJEITADO = 'REJEITADO', 'Rejeitado'

    # --- Relacionamentos ---
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE, related_name='notificacoes')
    usuario_reportou = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='notificacoes_feitas')
    resolvido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notificacoes_resolvidas')

    # --- Detalhes da Notificação ---
    tipo_erro = models.CharField(max_length=50, choices=TipoErro.choices)
    descricao = models.TextField(verbose_name="Descrição do erro")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    
    # --- Datas ---
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_resolucao = models.DateTimeField(null=True, blank=True)
    
    # --- CAMPO REMOVIDO ---
    # O campo `data_arquivamento` foi removido pois a funcionalidade de arquivar foi retirada.

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        # A constraint garante que um usuário não possa ter múltiplos reports PENDENTES para a mesma questão.
        constraints = [
            models.UniqueConstraint(
                fields=['questao', 'usuario_reportou'], 
                condition=Q(status='PENDENTE'),
                name='unique_active_report_per_user_per_question'
            )
        ]
        ordering = ['-data_criacao']

    def __str__(self):
        username = getattr(self.usuario_reportou, 'username', 'N/A')
        return f'Notificação para Q{self.questao.id} ({self.get_tipo_erro_display()}) por {username}'