# pratica/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RespostaUsuario
# =======================================================================
# IMPORTANDO ProfileGamificacao
# =======================================================================
from gamificacao.models import ProfileStreak, ProfileGamificacao
from usuarios.models import UserProfile

@receiver(post_save, sender=UserProfile)
def criar_perfis_gamificacao(sender, instance, created, **kwargs):
    """
    Cria os perfis de gamificação (Streak e XP/Nível) para cada novo UserProfile.
    """
    if created:
        ProfileStreak.objects.create(user_profile=instance)
        # =======================================================================
        # ADIÇÃO: Cria o perfil de XP/Nível automaticamente
        # =======================================================================
        ProfileGamificacao.objects.create(user_profile=instance)

@receiver(post_save, sender=RespostaUsuario)
def atualizar_streak_usuario(sender, instance, created, **kwargs):
    """
    Este signal agora foca apenas em atualizar o streak do usuário.
    """
    if not created:
        return

    user_profile = instance.usuario.userprofile
    streak_data, _ = ProfileStreak.objects.get_or_create(user_profile=user_profile)
    
    streak_data.update_streak()