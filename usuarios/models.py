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

    # O campo foto_perfil (upload) foi comentado/removido, como solicitado.
    # foto_perfil = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
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

    def __str__(self):
        return f"{self.nome} {self.sobrenome}"

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

def reenviar_ativacao(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                messages.info(request, 'Esta conta já está ativa. Você pode fazer o login.')
                return redirect('login')
            
            # Deleta qualquer token de ativação antigo para garantir que apenas o mais recente seja válido
            Ativacao.objects.filter(user=user).delete()
            
            # Cria um novo token de ativação
            ativacao = Ativacao.objects.create(user=user)
            
            # Envia o e-mail de confirmação
            enviar_email_com_template(
                request,
                subject='Confirme seu Cadastro no Raio-X da Aprovação',
                template_name='usuarios/email_confirmacao.html',
                context={'user': user, 'token': ativacao.token},
                recipient_list=[user.email]
            )
            
            messages.success(request, 'Um novo e-mail de ativação foi enviado para o seu endereço. Verifique sua caixa de entrada e spam.')
            return redirect('login')
            
        except User.DoesNotExist:
            messages.error(request, 'Nenhum usuário inativo encontrado com este e-mail.')
            return redirect('reenviar_ativacao')
    return render(request, 'usuarios/reenviar_ativacao.html')