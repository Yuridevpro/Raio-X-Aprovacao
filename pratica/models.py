# pratica/models.py

from django.db import models
from django.contrib.auth.models import User
from questoes.models import Questao

class RespostaUsuario(models.Model):
    # A resposta pertence a um usuário e a uma questão.
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    questao = models.ForeignKey(Questao, on_delete=models.CASCADE)
    
    # A alternativa que o usuário marcou (A, B, C, D, ou E).
    alternativa_selecionada = models.CharField(max_length=1)
    
    # Armazenamos se a resposta foi correta para facilitar as consultas.
    foi_correta = models.BooleanField()
    
    # Data em que a resposta foi dada.
    data_resposta = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Garante que um usuário só pode responder a mesma questão uma vez.
        # Se quisermos permitir que respondam de novo, teríamos que remover esta linha
        # ou adicionar um campo para identificar a "tentativa". Por ora, manteremos assim.
        unique_together = ('usuario', 'questao')

    def __str__(self):
        status = "Correta" if self.foi_correta else "Incorreta"
        return f"{self.usuario.username} - Questão {self.questao.id} - {status}"

# ADICIONE ESTE NOVO MODELO
class Comentario(models.Model):
    # O comentário pertence a uma questão e foi escrito por um usuário.
    questao = models.ForeignKey(Questao, related_name='comentarios', on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # O conteúdo do comentário.
    conteudo = models.TextField()
    
    # Data e hora de criação.
    data_criacao = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='comentarios_curtidos', blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='respostas')


    class Meta:
        # Ordena os comentários do mais novo para o mais antigo por padrão.
        ordering = ['data_criacao']

    def __str__(self):
        return f'Comentário de {self.usuario.username} na questão {self.questao.id}'
    

# --- INÍCIO DO NOVO MODELO ---
class FiltroSalvo(models.Model):
    # O filtro pertence a um usuário
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    # Um nome para o filtro, definido pelo usuário (ex: "Português - FGV")
    nome = models.CharField(max_length=100)
    # Armazenamos os parâmetros da URL de filtro
    # Ex: disciplina=1&disciplina=3&banca=2&status=errei
    parametros_url = models.TextField()
    
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Garante que um usuário não pode ter dois filtros com o mesmo nome
        unique_together = ('usuario', 'nome')
        ordering = ['-data_criacao']

    def __str__(self):
        return f'Filtro "{self.nome}" de {self.usuario.username}'