# gestao/models.py

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

# =======================================================================
# MODELOS DE SOLICITAÇÃO DE USUÁRIO COMUM (Sem alterações)
# =======================================================================

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


class PromocaoSuperuser(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        APROVADO = 'APROVADO', 'Aprovado'
        REJEITADO = 'REJEITADO', 'Rejeitado'

    QUORUM_IDEAL = 2 

    usuario_alvo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promocoes_recebidas')
    solicitado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promocoes_solicitadas')
    justificativa = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    
    aprovado_por = models.ManyToManyField(User, related_name='promocoes_aprovadas', blank=True)

    def get_quorum_necessario(self):
        outros_superusers_count = User.objects.filter(is_superuser=True, is_active=True).exclude(pk=self.solicitado_por.pk).count()
        if outros_superusers_count == 0:
            return float('inf')
        return min(self.QUORUM_IDEAL, outros_superusers_count)

    def aprovar(self, superuser_aprovador):
        if self.status != self.Status.PENDENTE:
            return False, "Esta solicitação não está mais pendente."
        if superuser_aprovador == self.solicitado_por:
            return False, "O solicitante não pode aprovar a própria solicitação."
        
        self.aprovado_por.add(superuser_aprovador)
        quorum_necessario = self.get_quorum_necessario()

        if quorum_necessario == float('inf'):
            return False, "Impossível aprovar: não há outros superusuários no sistema para formar um quorum."

        votos_atuais = self.aprovado_por.count()
        if votos_atuais >= quorum_necessario:
            self.status = self.Status.APROVADO
            self.usuario_alvo.is_superuser = True
            self.usuario_alvo.is_staff = True
            self.usuario_alvo.save(update_fields=['is_superuser', 'is_staff'])
            self.save(update_fields=['status'])
            return True, f"Quorum de {quorum_necessario} aprovações atingido. Usuário promovido com sucesso."
        
        self.save()
        votos_restantes = quorum_necessario - votos_atuais
        plural = "voto" if votos_restantes == 1 else "votos"
        return False, f"Aprovação registrada. Ainda falta(m) {votos_restantes} {plural} para a promoção ser efetivada."


# =======================================================================
# INÍCIO DA REFATORAÇÃO: CLASSE BASE ABSTRATA PARA LÓGICA DE QUÓRUM
# =======================================================================

# gestao/models.py

class BaseSuperuserQuorumRequest(models.Model):
    """
    Um modelo base abstrato que contém toda a lógica de quórum compartilhada
    para solicitações de despromoção e exclusão de superusuários.
    Isso evita a duplicação de código e centraliza as regras de negócio.
    """
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        APROVADO = 'APROVADO', 'Aprovado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    QUORUM_IDEAL = 2

    # Campos comuns a todas as solicitações de quórum
    justificativa = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    data_solicitacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True # Isso diz ao Django para não criar uma tabela para este modelo

    def get_quorum_necessario(self):
        """
        Calcula o número de aprovações necessárias.
        A lógica é a mesma para despromoção e exclusão.
        """
        outros_superusers_count = User.objects.filter(
            is_superuser=True, is_active=True
        ).exclude(
            pk=self.solicitado_por.pk
        ).exclude(
            pk=self.usuario_alvo.pk
        ).count()

        if outros_superusers_count == 0:
            return 1 # Apenas o alvo precisa aprovar
        return min(self.QUORUM_IDEAL, outros_superusers_count + 1)

    def _check_approval(self, superuser_aprovador):
        """
        Lógica central e genérica para processar uma aprovação.
        Retorna um status ('QUORUM_MET', 'APPROVAL_REGISTERED', 'FAILED') e uma mensagem.
        """
        if self.status != self.Status.PENDENTE:
            return 'FAILED', "Esta solicitação não está mais pendente."
        if superuser_aprovador == self.solicitado_por:
            return 'FAILED', "O solicitante não pode aprovar a própria solicitação."

        # Adiciona o aprovador à lista, a menos que seja o próprio alvo da solicitação
        if superuser_aprovador != self.usuario_alvo:
            self.aprovado_por.add(superuser_aprovador)
        
        votos_atuais = self.aprovado_por.count() + 1
        quorum_necessario = self.get_quorum_necessario()
        
        if votos_atuais >= quorum_necessario:
            self.status = self.Status.APROVADO
            # =======================================================================
            # CORREÇÃO FINAL: A linha foi movida para cá.
            # Salva o status APROVADO da solicitação. A view cuidará do resto.
            # Esta linha estava faltando no local correto, o que causava a falha nos testes.
            self.save(update_fields=['status'])
            # =======================================================================
            return 'QUORUM_MET', None  # A mensagem de sucesso será gerada pela classe filha
        else:
            self.save()  # Salva a adição do novo aprovador
            votos_restantes = quorum_necessario - votos_atuais
            return 'APPROVAL_REGISTERED', f"Aprovação registrada. Falta(m) {votos_restantes} voto(s)."

# =======================================================================
# MODELOS REATORADOS QUE HERDAM A LÓGICA DE QUÓRUM
# =======================================================================

class DespromocaoSuperuser(BaseSuperuserQuorumRequest):
    # Campos específicos com seus próprios 'related_name'
    usuario_alvo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='despromocoes_recebidas')
    solicitado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='despromocoes_solicitadas')
    aprovado_por = models.ManyToManyField(User, related_name='despromocoes_aprovadas', blank=True)

    def aprovar(self, superuser_aprovador):
        """
        Processa a aprovação e retorna uma mensagem de sucesso específica para despromoção.
        """
        status, message = self._check_approval(superuser_aprovador)
        if status == 'QUORUM_MET':
            if superuser_aprovador == self.usuario_alvo:
                message = f"Você confirmou sua própria despromoção. Suas permissões de superusuário foram removidas."
            else:
                message = f"Quorum atingido. Usuário {self.usuario_alvo.username} foi despromovido."
        return status, message

    def __str__(self):
        return f"Solicitação para despromover {self.usuario_alvo.username}"

class ExclusaoSuperuser(BaseSuperuserQuorumRequest):
    # Campos específicos com seus próprios 'related_name'
    usuario_alvo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exclusoes_superuser_recebidas')
    solicitado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exclusoes_superuser_solicitadas')
    aprovado_por = models.ManyToManyField(User, related_name='exclusoes_superuser_aprovadas', blank=True)

    def aprovar(self, superuser_aprovador):
        """
        Processa a aprovação e retorna uma mensagem de sucesso específica para exclusão.
        A view agora é 100% responsável por deletar o usuário.
        """
        status, message = self._check_approval(superuser_aprovador)
        if status == 'QUORUM_MET':
            if superuser_aprovador == self.usuario_alvo:
                 message = f"Você confirmou sua própria exclusão. Sua conta foi removida."
            else:
                message = f"Quorum atingido. Usuário {self.usuario_alvo.username} foi excluído."
        return status, message

    def __str__(self):
        return f"Solicitação para excluir o superusuário {self.usuario_alvo.username}"

# =======================================================================
# FIM DA REFATORAÇÃO
# =======================================================================
    
class LogAtividadeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def all_including_deleted(self):
        return super().get_queryset()

class LogAtividade(models.Model):
    # ... (O restante do arquivo LogAtividade e seus signals permanece exatamente o mesmo) ...
    class Acao(models.TextChoices):
        USUARIO_DELETADO = 'USUARIO_DELETADO', 'Usuário Deletado'
        PERMISSOES_ALTERADAS = 'PERMISSOES_ALTERADAS', 'Permissões de Usuário Alteradas'
        USUARIO_PROMOVIDO_SUPERUSER = 'USUARIO_PROMOVIDO_SUPERUSER', 'Usuário Promovido a Superuser'
        USUARIO_DESPROMOVIDO_SUPERUSER = 'USUARIO_DESPROMOVIDO_SUPERUSER', 'Usuário Despromovido de Superuser'
        SOLICITACAO_EXCLUSAO_CRIADA = 'SOLICITACAO_EXCLUSAO_CRIADA', 'Solicitação de Exclusão Criada'
        SOLICITACAO_EXCLUSAO_APROVADA = 'SOLICITACAO_EXCLUSAO_APROVADA', 'Solicitação de Exclusão Aprovada'
        SOLICITACAO_EXCLUSAO_REJEITADA = 'SOLICITACAO_EXCLUSAO_REJEITADA', 'Solicitação de Exclusão Rejeitada'
        SOLICITACAO_EXCLUSAO_CANCELADA = 'SOLICITACAO_EXCLUSAO_CANCELADA', 'Solicitação de Exclusão Cancelada'
        SOLICITACAO_PROMOCAO_CRIADA = 'SOLICITACAO_PROMOCAO_CRIADA', 'Solicitação de Promoção Criada'
        SOLICITACAO_PROMOCAO_APROVADA = 'SOLICITACAO_PROMOCAO_APROVADA', 'Aprovação de Promoção Registrada'
        SOLICITACAO_PROMOCAO_CANCELADA = 'SOLICITACAO_PROMOCAO_CANCELADA', 'Solicitação de Promoção Cancelada'
        SOLICITACAO_DESPROMOCAO_CRIADA = 'SOLICITACAO_DESPROMOCAO_CRIADA', 'Solicitação de Despromoção Criada'
        SOLICITACAO_DESPROMOCAO_APROVADA = 'SOLICITACAO_DESPROMOCAO_APROVADA', 'Aprovação de Despromoção Registrada'
        SOLICITACAO_DESPROMOCAO_CANCELADA = 'SOLICITACAO_DESPROMOCAO_CANCELADA', 'Solicitação de Despromoção Cancelada'
        SOLICITACAO_EXCLUSAO_SUPERUSER_CRIADA = 'SOLICITACAO_EXCLUSAO_SUPERUSER_CRIADA', 'Solicitação de Exclusão de Superusuário Criada'
        SOLICITACAO_EXCLUSAO_SUPERUSER_APROVADA = 'SOLICITACAO_EXCLUSAO_SUPERUSER_APROVADA', 'Aprovação de Exclusão de Superusuário Registrada'
        SOLICITACAO_EXCLUSAO_SUPERUSER_CANCELADA = 'SOLICITACAO_EXCLUSAO_SUPERUSER_CANCELADA', 'Solicitação de Exclusão de Superusuário Cancelada'
        QUESTAO_CRIADA = 'QUESTAO_CRIADA', 'Questão Criada'
        QUESTAO_EDITADA = 'QUESTAO_EDITADA', 'Questão Editada'
        QUESTAO_DELETADA = 'QUESTAO_DELETADA', 'Questão Deletada'
        ENTIDADE_CRIADA = 'ENTIDADE_CRIADA', 'Entidade Criada'
        ASSUNTO_CRIADO = 'ASSUNTO_CRIADO', 'Assunto Criado'
        NOTIFICACOES_RESOLVIDAS = 'NOTIFICACOES_RESOLVIDAS', 'Notificações Resolvidas'
        NOTIFICACOES_REJEITADAS = 'NOTIFICACOES_REJEITADAS', 'Notificações Rejeitadas'
        NOTIFICACOES_DELETADAS = 'NOTIFICACOES_DELETADAS', 'Notificações Deletadas'
        LOG_DELETADO = 'LOG_DELETADO', 'Log Deletado'

    ator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=50, choices=Acao.choices)
    alvo_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    alvo_id = models.PositiveIntegerField(null=True, blank=True)
    alvo = GenericForeignKey('alvo_content_type', 'alvo_id')
    detalhes = models.JSONField(default=dict, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_logs')
    hash_log = models.CharField(max_length=64, blank=True, null=True, unique=True, db_index=True)

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