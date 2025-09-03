# usuarios/models.py

from django.db import models
from django.contrib.auth.models import User
# Importe o modelo Questao
from questoes.models import Questao


from django.utils import timezone
from datetime import timedelta
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=100)
    
    # ADICIONE ESTE CAMPO
    # Um usuário pode ter muitas questões favoritas, e uma questão pode ser favoritada por muitos usuários.
    questoes_favoritas = models.ManyToManyField(Questao, blank=True)

    def __str__(self):
        return f"{self.nome} {self.sobrenome}"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        # O token expira em 1 hora
        return timezone.now() > self.created_at + timedelta(hours=1)