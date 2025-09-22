# pratica/signals.py (ARQUIVO CORRIGIDO E FINALIZADO)

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RespostaUsuario
from gamificacao.models import ProfileStreak, ProfileGamificacao
from usuarios.models import UserProfile

@receiver(post_save, sender=UserProfile)
def criar_perfis_gamificacao(sender, instance, created, **kwargs):
    """
    Cria os perfis de gamificação (Streak e XP/Nível/Moedas) para cada novo UserProfile.
    """
    if created:
        ProfileStreak.objects.get_or_create(user_profile=instance)
        ProfileGamificacao.objects.get_or_create(user_profile=instance)

@receiver(post_save, sender=RespostaUsuario)
def atualizar_streak_usuario(sender, instance, created, **kwargs):
    """
    Este signal foca apenas em atualizar o streak do usuário sempre que
    uma nova resposta é criada ou atualizada.
    """
    # Esta lógica é acionada tanto na criação quanto na atualização de uma RespostaUsuario
    user_profile = instance.usuario.userprofile
    streak_data, _ = ProfileStreak.objects.get_or_create(user_profile=user_profile)
    
    streak_data.update_streak()