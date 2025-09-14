# pratica/signals.py (NOVO ARQUIVO)

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RespostaUsuario
from gamificacao.models import ProfileStreak, Conquista, ConquistaUsuario
from usuarios.models import UserProfile

@receiver(post_save, sender=UserProfile)
def criar_perfil_streak(sender, instance, created, **kwargs):
    """
    Cria um objeto ProfileStreak para cada novo UserProfile.
    """
    if created:
        ProfileStreak.objects.create(user_profile=instance)

@receiver(post_save, sender=RespostaUsuario)
def verificar_gamificacao(sender, instance, created, **kwargs):
    """
    Este signal é disparado toda vez que uma resposta é salva.
    Ele chama as funções que verificam o streak e as conquistas.
    """
    if not created:
        return # Executa apenas na primeira resposta a uma questão

    user_profile = instance.usuario.userprofile
    streak_data, _ = ProfileStreak.objects.get_or_create(user_profile=user_profile)
    
    # 1. Atualizar o Streak
    streak_data.update_streak()
    
    # 2. Verificar Conquistas
    verificar_conquistas_de_streak(user_profile, streak_data.current_streak)
    verificar_conquistas_de_volume(user_profile)

def verificar_conquistas_de_streak(user_profile, current_streak):
    """ Verifica se o usuário atingiu um marco de streak. """
    streaks_marcos = {
        'STREAK_3_DIAS': 3,
        'STREAK_7_DIAS': 7,
        'STREAK_30_DIAS': 30,
    }
    
    for chave, dias in streaks_marcos.items():
        if current_streak >= dias:
            # Tenta buscar a conquista no banco
            try:
                conquista = Conquista.objects.get(chave=chave)
                # Tenta criar a relação, se não existir. get_or_create previne duplicatas.
                ConquistaUsuario.objects.get_or_create(user_profile=user_profile, conquista=conquista)
            except Conquista.DoesNotExist:
                # Se a conquista não foi cadastrada no admin, apenas ignora.
                pass

def verificar_conquistas_de_volume(user_profile):
    """ Verifica se o usuário atingiu um marco de total de questões resolvidas. """
    total_resolvidas = RespostaUsuario.objects.filter(usuario=user_profile.user).count()
    
    volume_marcos = {
        'PRIMEIRA_QUESTAO': 1,
        'DEZ_QUESTOES': 10,
        'CEM_QUESTOES': 100,
    }

    for chave, quantidade in volume_marcos.items():
        if total_resolvidas >= quantidade:
            try:
                conquista = Conquista.objects.get(chave=chave)
                ConquistaUsuario.objects.get_or_create(user_profile=user_profile, conquista=conquista)
            except Conquista.DoesNotExist:
                pass