# gestao/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.sites.models import Site

from .models import LogAtividade
from .utils import enviar_email_para_superusers

@receiver(post_save, sender=LogAtividade)
def alertar_sobre_acao_critica(sender, instance, created, **kwargs):
    """
    Signal que é acionado após um LogAtividade ser salvo.
    Verifica se a ação é crítica e, em caso afirmativo, envia um alerta.
    """
    if not created:
        return

    # Limite de volume para disparar o alerta
    LIMITE_ALERTA_EXCLUSAO = 50 
    
    # 1. Alerta para tentativa de exclusão em massa que excedeu o limite de volume
    if instance.acao == LogAtividade.Acao.TENTATIVA_EXCLUSAO_MASSA_EXCEDIDA:
        quantidade = instance.detalhes.get('quantidade_tentada', 'N/A')
        limite = instance.detalhes.get('limite', 'N/A')
        
        subject = f"Tentativa de exclusão em massa bloqueada"
        message = (
            f"O usuário '{instance.ator.username}' tentou excluir {quantidade} questões de uma só vez, "
            f"mas a ação foi bloqueada pois o limite é de {limite} itens por operação.\n\n"
            f"Data/Hora: {instance.data_criacao.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"Acesse o painel de gestão para mais detalhes."
        )
        enviar_email_para_superusers(subject, message)

    # 2. Alerta para exclusão em massa (bem-sucedida) acima do limite de alerta
    if instance.acao == LogAtividade.Acao.QUESTAO_DELETADA and 'Ação de exclusão em massa' in instance.detalhes.get('motivo', ''):
        count = instance.detalhes.get('count', 0)
        
        if count > LIMITE_ALERTA_EXCLUSAO:
            current_site = Site.objects.get_current()
            logs_url = f"http://{current_site.domain}{reverse('gestao:listar_logs_atividade')}"
            
            subject = f"Exclusão em massa de {count} questões realizada"
            message = (
                f"O usuário '{instance.ator.username}' moveu {count} questões para a lixeira em uma única operação.\n\n"
                f"Data/Hora: {instance.data_criacao.strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"Recomendamos que você verifique esta atividade no registro de logs da plataforma.\n\n"
                f"Ver Logs: {logs_url}"
            )
            enviar_email_para_superusers(subject, message)