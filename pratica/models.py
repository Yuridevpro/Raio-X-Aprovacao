# pratica/models.py (VERSÃO DE TRANSIÇÃO - PASSO 1)

from django.db import models
from django.contrib.auth.models import User
from questoes.models import Questao
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

# =======================================================================
# MODELOS DE DADOS DE INTERAÇÃO DO USUÁRIO
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
    # Relacionamentos
    questao = models.ForeignKey(Questao, related_name='comentarios', on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='respostas')
    
    # Conteúdo
    conteudo = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='comentarios_curtidos', blank=True)
    notificacoes = GenericRelation('pratica.Notificacao')

    class Meta:
        ordering = ['data_criacao']
    def __str__(self):
        return f'Comentário de {self.usuario.username} na questão {self.questao.id} (ID: {self.id})'
    
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
# MODELO DE NOTIFICAÇÃO (VERSÃO DE TRANSIÇÃO PARA MIGRAÇÃO DE DADOS)
# =======================================================================

class Notificacao(models.Model):
    class TipoErro(models.TextChoices):
        # Tipos para Questões
        ENUNCIADO_ALTERNATIVA = 'ENUNCIADO_ALTERNATIVA', 'Enunciado/alternativa errada'
        DISCIPLINA_ASSUNTO = 'DISCIPLINA_ASSUNTO', 'Disciplina ou assunto errado'
        QUESTAO_ANULADA = 'QUESTAO_ANULADA', 'Questão anulada'
        QUESTAO_DESATUALIZADA = 'QUESTAO_DESATUALIZADA', 'Questão desatualizada'
        QUESTAO_DUPLICADA = 'QUESTAO_DUPLICADA', 'Questão duplicada'
        # Tipos para Comentários
        COMENTARIO_OFENSIVO = 'COMENTARIO_OFENSIVO', 'Conteúdo ofensivo ou inadequado'
        COMENTARIO_SPAM = 'COMENTARIO_SPAM', 'Spam ou propaganda'
        COMENTARIO_OUTRO = 'COMENTARIO_OUTRO', 'Outro problema no comentário'

    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        RESOLVIDO = 'RESOLVIDO', 'Resolvido'
        REJEITADO = 'REJEITADO', 'Rejeitado'

    # --- Campo de Transição e Novos Campos (Temporariamente Nulos) ---
    # O campo `questao` antigo é mantido para que possamos ler os dados dele.
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE, related_name='notificacoes_temp', null=True, blank=True)
    
    # Os novos campos são criados permitindo nulos para que a migração estrutural passe.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    alvo = GenericForeignKey('content_type', 'object_id')
    
    # --- Atores da Notificação ---
    usuario_reportou = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='notificacoes_feitas')
    resolvido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notificacoes_resolvidas')

    # --- Detalhes da Notificação ---
    tipo_erro = models.CharField(max_length=50, choices=TipoErro.choices)
    descricao = models.TextField(verbose_name="Descrição do erro")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    
    # --- Datas ---
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_resolucao = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Notificação/Denúncia"
        verbose_name_plural = "Notificações & Denúncias"
        # =======================================================================
        # INÍCIO DA CORREÇÃO: Garantindo a constraint de unicidade
        # =======================================================================
        # Esta constraint impede que o mesmo usuário crie mais de uma notificação
        # com o status 'PENDENTE' para o mesmo objeto (seja uma questão ou um comentário).
        # É a defesa mais forte contra reports duplicados.
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'usuario_reportou'], 
                condition=Q(status='PENDENTE'),
                name='unique_active_report_per_user_per_object'
            )
        ]
        # =======================================================================
        # FIM DA CORREÇÃO
        # =======================================================================
        ordering = ['-data_criacao']

    def __str__(self):
        return f'Notificação para {self.alvo} por {getattr(self.usuario_reportou, "username", "N/A")}'