# questoes/models.py

from django.db import models
from django.contrib.auth.models import User
import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta  # Importar timedelta
from storages.backends.s3boto3 import S3Boto3Storage

# ... (outros modelos como Disciplina, Banca, etc. permanecem os mesmos) ...

s3_storage = S3Boto3Storage()

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

class QuestaoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class Questao(models.Model):
    GABARITO_CHOICES = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E')]

    # Campos...
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    assunto = models.ForeignKey(Assunto, on_delete=models.PROTECT)
    banca = models.ForeignKey(Banca, on_delete=models.PROTECT, null=True, blank=True)
    codigo = models.CharField(max_length=20, unique=True, null=True, blank=True)
    instituicao = models.ForeignKey(Instituicao, on_delete=models.PROTECT, null=True, blank=True)
    ano = models.IntegerField(null=True, blank=True)
    imagem_enunciado = models.ImageField(upload_to='enunciado_pics/', storage=s3_storage, null=True, blank=True)
    enunciado = models.TextField()
    alternativas = models.JSONField()
    gabarito = models.CharField(max_length=1, choices=GABARITO_CHOICES)
    explicacao = models.TextField(blank=True, null=True)
    is_inedita = models.BooleanField(default=False, verbose_name="É inédita?")
    criada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="questoes_criadas")
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="questoes_deletadas")

    objects = QuestaoManager()
    all_objects = models.Manager()

    # =======================================================================
    # INÍCIO DA ADIÇÃO: Propriedade para lógica de negócio
    # =======================================================================
    @property
    def is_permanently_deletable(self):
        """Verifica se a questão está na lixeira há mais de 20 dias."""
        if not self.is_deleted or not self.deleted_at:
            return False
        return timezone.now() > self.deleted_at + timedelta(days=20)
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================

    def __str__(self):
        banca_ano = f"{self.banca.nome} - {self.ano}" if self.banca and self.ano else "Inédita"
        return f"[{banca_ano}] {self.enunciado[:50]}..."
        
    def get_alternativas_dict(self):
        if isinstance(self.alternativas, str):
            try: return json.loads(self.alternativas)
            except json.JSONDecodeError: return {}
        return self.alternativas

    def delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()

    def hard_delete(self):
        super(Questao, self).delete()
    
@receiver(post_save, sender=Questao)
def gerar_codigo_questao(sender, instance, created, **kwargs):
    if created and not instance.codigo:
        instance.codigo = f'Q{instance.id}'
        instance.save(update_fields=['codigo'])