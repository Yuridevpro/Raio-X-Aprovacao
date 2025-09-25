# usuarios/models.py
from django.db import models
from django.contrib.auth.models import User
from questoes.models import Questao
from django.utils import timezone
from datetime import timedelta
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=100)
    questoes_favoritas = models.ManyToManyField(Questao, blank=True)
    
    avatar_equipado = models.ForeignKey(
        'gamificacao.Avatar', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='usuarios_com_avatar'
    )
    borda_equipada = models.ForeignKey(
        'gamificacao.Borda', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='usuarios_com_borda'
    )
    
    banner_equipado = models.ForeignKey(
        'gamificacao.Banner',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='usuarios_com_banner'
    )

    def __str__(self):
        return f"{self.nome} {self.sobrenome}"

    # =======================================================================
    # INÍCIO DA ADIÇÃO: Propriedade para contagem correta
    # =======================================================================
    @property
    def pending_rewards_count(self):
        """
        Retorna a contagem APENAS de recompensas pendentes (não resgatadas).
        Usa uma importação local para evitar importação circular.
        """
        from gamificacao.models import RecompensaPendente
        return RecompensaPendente.objects.filter(
            user_profile=self, 
            resgatado_em__isnull=True
        ).count()
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================

# --- Modelos de Ativação e Reset (sem alterações) ---
class Ativacao(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(days=1)
        
    def __str__(self):
        return f"Token de Ativação para {self.user.username}"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(hours=1)
    
    def __str__(self):
        return f"Token de Reset para {self.user.username}"