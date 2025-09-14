# gamificacao/models.py (NOVO ARQUIVO)

from django.db import models
from django.contrib.auth.models import User
from usuarios.models import UserProfile
from django.utils import timezone
from datetime import date

class ProfileStreak(models.Model):
    """ Armazena os dados de sequência (streak) de um usuário. """
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='streak_data')
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    last_practice_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Streak de {self.user_profile.user.username}: {self.current_streak} dias"

    def update_streak(self):
        """
        Lógica central para atualizar a sequência de prática.
        Deve ser chamada sempre que um usuário resolve a primeira questão do dia.
        """
        today = date.today()
        
        # Se já praticou hoje, não faz nada
        if self.last_practice_date == today:
            return

        # Verifica se a última prática foi ontem
        if self.last_practice_date and (today - self.last_practice_date).days == 1:
            self.current_streak += 1
        else:
            # Se não foi ontem (ou se nunca praticou), reseta para 1
            self.current_streak = 1
        
        self.last_practice_date = today
        
        # Atualiza a maior sequência já alcançada
        if self.current_streak > self.max_streak:
            self.max_streak = self.current_streak
            
        self.save()

class Conquista(models.Model):
    """ Define uma conquista que pode ser desbloqueada. """
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    icone = models.CharField(max_length=50, help_text="Ex: 'fas fa-fire' (classes do Font Awesome)")
    cor = models.CharField(max_length=20, default='gold', help_text="Cor do ícone (ex: 'gold', '#FFD700')")
    
    # Chave única para verificação no código
    chave = models.CharField(max_length=50, unique=True, help_text="Identificador único, ex: 'STREAK_7_DIAS'")

    def __str__(self):
        return self.nome

class ConquistaUsuario(models.Model):
    """ Liga um usuário a uma conquista desbloqueada. """
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='conquistas')
    conquista = models.ForeignKey(Conquista, on_delete=models.CASCADE)
    data_conquista = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_profile', 'conquista') # Um usuário só pode ter cada conquista uma vez

    def __str__(self):
        return f"{self.user_profile.user.username} desbloqueou {self.conquista.nome}"


