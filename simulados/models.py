from django.db import models
from django.contrib.auth.models import User
from questoes.models import Questao
from django.utils import timezone
# ✅ ADIÇÃO: Importações para o sinal
from django.db.models.signals import post_save
from django.dispatch import receiver

# ✅ ADIÇÃO: Classe de choices para o status
class StatusSimulado(models.TextChoices):
    ATIVO = 'ATIVO', 'Ativo'
    EM_BREVE = 'EM_BREVE', 'Em Breve'
    ARQUIVADO = 'ARQUIVADO', 'Arquivado'

class Simulado(models.Model):
    """ Representa um conjunto de questões que compõem um simulado. """
    nome = models.CharField(max_length=200)
    questoes = models.ManyToManyField(Questao, blank=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    is_oficial = models.BooleanField(default=False, verbose_name="É um simulado oficial?")
    filtros_iniciais = models.JSONField(
        null=True, 
        blank=True, 
        help_text="Filtros usados na criação para definir o pool de questões."
    )
    # =======================================================================
    # INÍCIO DAS NOVAS ADIÇÕES
    # =======================================================================
    codigo = models.CharField(max_length=20, unique=True, null=True, blank=True, help_text="Código único do simulado, gerado automaticamente.")
    status = models.CharField(
        max_length=10, 
        choices=StatusSimulado.choices, 
        default=StatusSimulado.ATIVO,
        db_index=True # Adicionar índice para otimizar a filtragem por status
    )
    # =======================================================================
    # FIM DAS NOVAS ADIÇÕES
    # =======================================================================
    
    def __str__(self):
        return self.nome

# ✅ ADIÇÃO: Sinal para gerar o código único após a criação do simulado
@receiver(post_save, sender=Simulado)
def gerar_codigo_simulado(sender, instance, created, **kwargs):
    if created and not instance.codigo:
        instance.codigo = f'SML-{instance.id}'
        instance.save(update_fields=['codigo'])


class SessaoSimulado(models.Model):
    """ Representa a tentativa de um usuário de resolver um simulado. """
    simulado = models.ForeignKey(Simulado, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim = models.DateTimeField(null=True, blank=True)
    finalizado = models.BooleanField(default=False)

    def __str__(self):
        return f"Sessão de {self.usuario.username} em {self.simulado.nome}"

    def finalizar_sessao(self):
        """ Marca a sessão como finalizada e registra a data/hora. """
        self.finalizado = True
        self.data_fim = timezone.now()
        self.save()

class RespostaSimulado(models.Model):
    """ Armazena a resposta de um usuário para uma questão dentro de uma sessão. """
    sessao = models.ForeignKey(SessaoSimulado, on_delete=models.CASCADE, related_name='respostas')
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE)
    alternativa_selecionada = models.CharField(max_length=1, null=True, blank=True)
    foi_correta = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ('sessao', 'questao')