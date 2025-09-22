# # simulados/signals.py

# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import SessaoSimulado
# from gamificacao.models import Conquista, ConquistaUsuario

# @receiver(post_save, sender=SessaoSimulado)
# def verificar_conquista_primeiro_simulado(sender, instance, **kwargs):
#     """
#     Disparado quando uma SessaoSimulado é salva. Verifica se é a primeira
#     vez que o usuário finaliza um simulado.
#     """
#     # Ação ocorre apenas quando o simulado é finalizado (o campo 'finalizado' vira True)
#     if instance.finalizado and instance.pk:
#         usuario = instance.usuario
        
#         # Conta quantos outros simulados finalizados este usuário possui.
#         # Excluímos o atual (instance.pk) para garantir a contagem correta.
#         outros_simulados_finalizados = SessaoSimulado.objects.filter(
#             usuario=usuario,
#             finalizado=True
#         ).exclude(pk=instance.pk).count()

#         # Se não há outros, este é o primeiro.
#         if outros_simulados_finalizados == 0:
#             try:
#                 conquista = Conquista.objects.get(chave='PRIMEIRO_SIMULADO')
#                 ConquistaUsuario.objects.get_or_create(
#                     user_profile=usuario.userprofile, 
#                     conquista=conquista
#                 )
#             except Conquista.DoesNotExist:
#                 # Se a conquista não foi cadastrada no admin, apenas ignora.
#                 pass