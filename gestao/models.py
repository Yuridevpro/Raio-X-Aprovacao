import hashlib
import json
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

# O modelo SolicitacaoExclusao permanece o mesmo, você não precisa alterá-lo.
class SolicitacaoExclusao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        APROVADO = 'APROVADO', 'Aprovado'
        REJEITADO = 'REJEITADO', 'Rejeitado'

    usuario_a_ser_excluido = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solicitacoes_de_exclusao')
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='solicitacoes_feitas')
    motivo = models.TextField(verbose_name="Justificativa da Solicitação")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitacoes_revisadas')
    data_revisao = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Solicitação de Exclusão"
        verbose_name_plural = "Solicitações de Exclusão"
        ordering = ['-data_solicitacao']

    def __str__(self):
        return f"Solicitação para excluir {self.usuario_a_ser_excluido.username} por {self.solicitado_por.username}"


# =======================================================================
# NOVO MODELO: Gerenciamento de Promoções a Superuser
# =======================================================================
class PromocaoSuperuser(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        APROVADO = 'APROVADO', 'Aprovado'
        REJEITADO = 'REJEITADO', 'Rejeitado'

    # Número de aprovações ADICIONAIS necessárias (além do solicitante)
    QUORUM_MINIMO = 2

    usuario_alvo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promocoes_recebidas')
    solicitado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promocoes_solicitadas')
    justificativa = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    
    aprovado_por = models.ManyToManyField(User, related_name='promocoes_aprovadas', blank=True)

    def aprovar(self, superuser_aprovador):
        if superuser_aprovador == self.solicitado_por:
            return False, "O solicitante não pode aprovar a própria solicitação."

        self.aprovado_por.add(superuser_aprovador)

        if self.aprovado_por.count() >= self.QUORUM_MINIMO:
            self.status = self.Status.APROVADO
            self.usuario_alvo.is_superuser = True
            self.usuario_alvo.is_staff = True
            self.usuario_alvo.save()
            self.save()
            # Log da promoção final
            criar_log(
                ator=self.solicitado_por,
                acao=LogAtividade.Acao.USUARIO_PROMOVIDO_SUPERUSER,
                alvo=self.usuario_alvo,
                detalhes={
                    'usuario_alvo': self.usuario_alvo.username,
                    'aprovadores': list(self.aprovado_por.all().values_list('username', flat=True))
                }
            )
            return True, "Quorum atingido. Usuário promovido."
        
        self.save()
        return False, "Aprovação registrada. Aguardando mais aprovações."

# =======================================================================
# MANAGER E MODELO LogAtividade ATUALIZADOS PARA AUDITORIA
# =======================================================================
class LogAtividadeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False, is_archived=False)

    def all_including_deleted(self):
        return super().get_queryset().filter(is_archived=False)

class LogAtividade(models.Model):
    class Acao(models.TextChoices):
        USUARIO_DELETADO = 'USUARIO_DELETADO', 'Usuário Deletado'
        PERMISSOES_ALTERADAS = 'PERMISSOES_ALTERADAS', 'Permissões de Usuário Alteradas'
        USUARIO_PROMOVIDO_SUPERUSER = 'USUARIO_PROMOVIDO_SUPERUSER', 'Usuário Promovido a Superuser'
        USUARIO_DESPROMOVIDO_SUPERUSER = 'USUARIO_DESPROMOVIDO_SUPERUSER', 'Usuário Despromovido de Superuser'
        SOLICITACAO_EXCLUSAO_CRIADA = 'SOLICITACAO_EXCLUSAO_CRIADA', 'Solicitação de Exclusão Criada'
        SOLICITACAO_EXCLUSAO_APROVADA = 'SOLICITACAO_EXCLUSAO_APROVADA', 'Solicitação de Exclusão Aprovada'
        SOLICITACAO_EXCLUSAO_REJEITADA = 'SOLICITACAO_EXCLUSAO_REJEITADA', 'Solicitação de Exclusão Rejeitada'
        SOLICITACAO_EXCLUSAO_CANCELADA = 'SOLICITACAO_EXCLUSAO_CANCELADA', 'Solicitação de Exclusão Cancelada'
        QUESTAO_CRIADA = 'QUESTAO_CRIADA', 'Questão Criada'
        QUESTAO_EDITADA = 'QUESTAO_EDITADA', 'Questão Editada'
        QUESTAO_DELETADA = 'QUESTAO_DELETADA', 'Questão Deletada'
        ENTIDADE_CRIADA = 'ENTIDADE_CRIADA', 'Entidade Criada'
        ASSUNTO_CRIADO = 'ASSUNTO_CRIADO', 'Assunto Criado'
        NOTIFICACOES_RESOLVIDAS = 'NOTIFICACOES_RESOLVIDAS', 'Notificações Resolvidas'
        NOTIFICACOES_REJEITADAS = 'NOTIFICACOES_REJEITADAS', 'Notificações Rejeitadas'
        NOTIFICACOES_DELETADAS = 'NOTIFICACOES_DELETADAS', 'Notificações Deletadas'
        LOG_DELETADO = 'LOG_DELETADO', 'Log Deletado' # Ação para o meta-log, se decidir usá-la

    ator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Usuário que realizou a ação.")
    acao = models.CharField(max_length=50, choices=Acao.choices, help_text="A ação que foi realizada.")
    alvo_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    alvo_id = models.PositiveIntegerField(null=True, blank=True)
    alvo = GenericForeignKey('alvo_content_type', 'alvo_id')
    detalhes = models.JSONField(default=dict, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    # Campos de Auditoria
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_logs')
    hash_log = models.CharField(max_length=64, blank=True, null=True, unique=True, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)

    objects = LogAtividadeManager()
    all_logs = models.Manager()

    class Meta:
        ordering = ['-data_criacao']
        verbose_name = "Registro de Atividade"
        verbose_name_plural = "Registros de Atividades"

    def __str__(self):
        ator_nome = self.ator.username if self.ator else "Sistema"
        return f'{self.get_acao_display()} por {ator_nome} em {self.data_criacao.strftime("%d/%m/%Y %H:%M")}'
    
    def delete(self, user=None):
        """Sobrescreve o delete para fazer o soft delete."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(using=self._state.db)


@receiver(post_save, sender=LogAtividade)
def calcular_hash_log(sender, instance, created, **kwargs):
    if created and not instance.hash_log:
        last_log = LogAtividade.all_logs.exclude(id=instance.id).order_by('-id').first()
        previous_hash = last_log.hash_log if last_log else '0' * 64
        
        log_data_str = (
            f"{instance.id}{instance.data_criacao.isoformat()}"
            f"{instance.ator_id}{instance.acao}{json.dumps(instance.detalhes, sort_keys=True)}"
            f"{previous_hash}"
        )
        
        sha256 = hashlib.sha256(log_data_str.encode('utf-8')).hexdigest()
        
        LogAtividade.all_logs.filter(id=instance.id).update(hash_log=sha256)