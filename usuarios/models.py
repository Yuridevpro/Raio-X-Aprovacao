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
    foto_perfil = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return f"{self.nome} {self.sobrenome}"

# --- INÍCIO DOS NOVOS MODELOS ---
class Ativacao(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        # Token de ativação expira em 24 horas
        return timezone.now() > self.created_at + timedelta(days=1)
        
    def __str__(self):
        return f"Token de Ativação para {self.user.username}"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        # Token de reset expira em 1 hora
        return timezone.now() > self.created_at + timedelta(hours=1)
    
    def __str__(self):
        return f"Token de Reset para {self.user.username}"
# --- FIM DOS NOVOS MODELOS ---