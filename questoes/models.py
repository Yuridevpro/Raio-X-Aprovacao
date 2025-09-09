# questoes/models.py

from django.db import models
from django.contrib.auth.models import User
import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from storages.backends.s3boto3 import S3Boto3Storage

# =======================================================================
# INÍCIO DA MODIFICAÇÃO
# =======================================================================
# 1. Cria uma instância explícita do backend de armazenamento do S3.
s3_storage = S3Boto3Storage()
# =======================================================================
# FIM DA MODIFICAÇÃO
# =======================================================================

class Disciplina(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nome

class Banca(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nome

class Instituicao(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nome

class Assunto(models.Model):
    nome = models.CharField(max_length=100)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('nome', 'disciplina')
    def __str__(self):
        return f"{self.nome} ({self.disciplina.nome})"

class Questao(models.Model):
    GABARITO_CHOICES = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E')]

    # Relacionamentos
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    assunto = models.ForeignKey(Assunto, on_delete=models.PROTECT)
    banca = models.ForeignKey(Banca, on_delete=models.PROTECT, null=True, blank=True)
    codigo = models.CharField(max_length=20, unique=True, null=True, blank=True)
    instituicao = models.ForeignKey(Instituicao, on_delete=models.PROTECT, null=True, blank=True)
    
    ano = models.IntegerField(null=True, blank=True)

    # =======================================================================
    # INÍCIO DA MODIFICAÇÃO
    # =======================================================================
    # 2. Adiciona o argumento 'storage=s3_storage' para forçar este campo a usar o S3.
    imagem_enunciado = models.ImageField(upload_to='enunciado_pics/', storage=s3_storage, null=True, blank=True)
    # =======================================================================
    # FIM DA MODIFICAÇÃO
    # =======================================================================
    
    enunciado = models.TextField()
    alternativas = models.JSONField()
    gabarito = models.CharField(max_length=1, choices=GABARITO_CHOICES)
    explicacao = models.TextField(blank=True, null=True)
    is_inedita = models.BooleanField(default=False, verbose_name="É inédita?")
    criada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        banca_ano = f"{self.banca.nome} - {self.ano}" if self.banca and self.ano else "Inédita"
        return f"[{banca_ano}] {self.enunciado[:50]}..."
        
    def get_alternativas_dict(self):
        if isinstance(self.alternativas, str):
            try: return json.loads(self.alternativas)
            except json.JSONDecodeError: return {}
        return self.alternativas
    
@receiver(post_save, sender=Questao)
def gerar_codigo_questao(sender, instance, created, **kwargs):
    """
    Gera um código único para a questão no formato Q + ID.
    O signal post_save é usado para garantir que a instância já tenha um ID.
    """
    if created and not instance.codigo:
        instance.codigo = f'Q{instance.id}'
        instance.save(update_fields=['codigo'])