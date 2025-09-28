# gamificacao/signals.py
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import Conquista

@receiver(pre_delete, sender=Conquista)
def verificar_dependencias_antes_de_excluir(sender, instance, **kwargs):
    """
    Impede a exclusão de uma Conquista se ela for um pré-requisito
    para qualquer outra conquista no sistema.
    """
    # Procura por todas as conquistas que têm a 'instance' (a que está sendo deletada)
    # na sua lista de pré-requisitos.
    conquistas_dependentes = Conquista.objects.filter(pre_requisitos=instance)

    if conquistas_dependentes.exists():
        # Se encontrar alguma, monta uma mensagem de erro clara
        nomes_dependentes = ", ".join([f"'{c.nome}'" for c in conquistas_dependentes])
        raise ValidationError(
            f"Não é possível excluir a conquista '{instance.nome}', pois ela é um pré-requisito "
            f"para as seguintes conquistas: {nomes_dependentes}. Por favor, remova a dependência "
            f"dessas conquistas antes de prosseguir."
        )