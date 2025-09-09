# gestao/models.py
from django.db import models
from django.conf import settings # Melhor prática para referenciar o User model

class SolicitacaoExclusao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        APROVADO = 'APROVADO', 'Aprovado'
        REJEITADO = 'REJEITADO', 'Rejeitado'

    usuario_a_ser_excluido = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, # Se o usuário for deletado por outro meio, a solicitação some.
        related_name='solicitacoes_de_exclusao'
    )
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Preserva o registro mesmo se o staff que pediu for excluído.
        null=True,
        related_name='solicitacoes_feitas'
    )
    motivo = models.TextField(verbose_name="Justificativa da Solicitação")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    
    # Campos para auditoria
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='solicitacoes_revisadas'
    )
    data_revisao = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Solicitação de Exclusão"
        verbose_name_plural = "Solicitações de Exclusão"
        ordering = ['-data_solicitacao']

    def __str__(self):
        return f"Solicitação para excluir {self.usuario_a_ser_excluido.username} por {self.solicitado_por.username}"