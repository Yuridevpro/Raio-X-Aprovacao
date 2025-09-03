# questoes/models.py

from django.db import models
from django.contrib.auth.models import User
import json
from django.db.models.signals import post_save # Importe o 'post_save'
from django.dispatch import receiver # Importe o 'receiver'

class Disciplina(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nome

class Banca(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nome

# --- INÍCIO DO NOVO MODELO ---
class Instituicao(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nome
# --- FIM DO NOVO MODELO ---

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

    # --- CAMPO ADICIONADO ---
    instituicao = models.ForeignKey(Instituicao, on_delete=models.PROTECT, null=True, blank=True)
    
    ano = models.IntegerField(null=True, blank=True)
    imagem_enunciado = models.ImageField(upload_to='enunciado_pics/', null=True, blank=True)
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
    
    # --- INÍCIO DO NOVO CÓDIGO (SIGNAL) ---
# Esta função será executada toda vez que uma nova Questao for salva.
@receiver(post_save, sender=Questao)
def gerar_codigo_questao(sender, instance, created, **kwargs):
    """
    Gera um código único para a questão no formato Q + ID.
    O signal post_save é usado para garantir que a instância já tenha um ID.
    """
    # 'created' é True apenas na primeira vez que o objeto é salvo.
    if created and not instance.codigo:
        # Formata o código e salva a instância novamente, sem disparar o signal de novo.
        instance.codigo = f'Q{instance.id}'
        instance.save(update_fields=['codigo'])
# --- FIM DO NOVO CÓDIGO ---