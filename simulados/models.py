# simulados/models.py

from django.db import models
from django.contrib.auth.models import User
from questoes.models import Questao
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver



class StatusSimulado(models.TextChoices):
    ATIVO = 'ATIVO', 'Ativo'
    EM_BREVE = 'EM_BREVE', 'Em Breve'
    ARQUIVADO = 'ARQUIVADO', 'Arquivado'

class NivelDificuldade(models.TextChoices):
    FACIL = 'FACIL', 'Fácil'
    MEDIO = 'MEDIO', 'Médio'
    DIFICIL = 'DIFICIL', 'Difícil'

class Simulado(models.Model):
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
    codigo = models.CharField(max_length=20, unique=True, null=True, blank=True, help_text="Código único do simulado, gerado automaticamente.")
    status = models.CharField(
        max_length=10, 
        choices=StatusSimulado.choices, 
        default=StatusSimulado.ATIVO,
        db_index=True
    )
    dificuldade = models.CharField(
        max_length=10,
        choices=NivelDificuldade.choices,
        default=NivelDificuldade.MEDIO,
        verbose_name="Nível de Dificuldade",
        help_text="Visível apenas para simulados oficiais."
    )
    tempo_por_questao = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        help_text="Tempo médio em minutos por questão. Nulo significa tempo ilimitado."
    )
    
    def __str__(self):
        return self.nome

@receiver(post_save, sender=Simulado)
def gerar_codigo_simulado(sender, instance, created, **kwargs):
    if created and not instance.codigo:
        instance.codigo = f'SML-{instance.id}'
        instance.save(update_fields=['codigo'])


class SessaoSimulado(models.Model):
    simulado = models.ForeignKey(Simulado, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim = models.DateTimeField(null=True, blank=True)
    finalizado = models.BooleanField(default=False)

    def __str__(self):
        return f"Sessão de {self.usuario.username} em {self.simulado.nome}"

    def finalizar_sessao(self):
        self.finalizado = True
        self.data_fim = timezone.now()
        self.save()

class RespostaSimulado(models.Model):
    sessao = models.ForeignKey(SessaoSimulado, on_delete=models.CASCADE, related_name='respostas')
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE)
    alternativa_selecionada = models.CharField(max_length=1, null=True, blank=True)
    foi_correta = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ('sessao', 'questao')