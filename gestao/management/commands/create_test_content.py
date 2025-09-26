# gestao/management/commands/create_test_content.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from questoes.models import Questao, Disciplina, Assunto, Banca, Instituicao
from pratica.models import Comentario
import random

class Command(BaseCommand):
    help = 'Popula o banco de dados com conteúdo de teste (Disciplinas, Bancas, Questões, Comentários).'

    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.NOTICE('Iniciando a criação de conteúdo de teste...'))

        # --- 1. LIMPAR DADOS ANTIGOS ---
        self.stdout.write(self.style.WARNING('Limpando conteúdo de teste antigo...'))
        Questao.objects.filter(enunciado__startswith='[TESTE]').delete()
        Disciplina.objects.filter(nome__startswith='[TESTE]').delete()
        Banca.objects.filter(nome__startswith='[TESTE]').delete()
        self.stdout.write(self.style.SUCCESS('Conteúdo antigo limpo.'))

        # --- 2. CRIAR ENTIDADES BASE ---
        disciplinas = [Disciplina.objects.create(nome=f'[TESTE] {d}') for d in ['Direito Constitucional', 'Português', 'Matemática Financeira', 'Informática']]
        bancas = [Banca.objects.create(nome=f'[TESTE] {b}') for b in ['FGV', 'Cesgranrio', 'Cebraspe']]
        instituicoes = [Instituicao.objects.create(nome=f'[TESTE] {i}') for i in ['Banco do Brasil', 'Caixa Econômica', 'Polícia Federal']]
        
        assuntos = []
        for d in disciplinas:
            for i in range(3):
                assuntos.append(Assunto.objects.create(disciplina=d, nome=fake.bs().title()))

        # --- 3. CRIAR QUESTÕES ---
        self.stdout.write(self.style.NOTICE('Criando 80 questões de teste...'))
        admin_user = User.objects.filter(is_superuser=True).first()
        for i in range(80):
            disciplina = random.choice(disciplinas)
            assuntos_da_disciplina = [a for a in assuntos if a.disciplina == disciplina]
            
            Questao.objects.create(
                disciplina=disciplina,
                assunto=random.choice(assuntos_da_disciplina),
                banca=random.choice(bancas),
                instituicao=random.choice(instituicoes),
                ano=random.randint(2020, 2024),
                enunciado=f"[TESTE] {fake.paragraph(nb_sentences=3)}",
                alternativas={letra: fake.sentence(nb_words=10) for letra in 'ABCDE'},
                gabarito=random.choice(['A', 'B', 'C', 'D', 'E']),
                explicacao=f"<h3>Gabarito Comentado</h3><p>{fake.paragraph(nb_sentences=5)}</p><ul><li>Ponto 1</li><li>Ponto 2</li></ul>",
                criada_por=admin_user,
                is_inedita=random.choice([True, False])
            )
        self.stdout.write(self.style.SUCCESS('-> 80 questões criadas.'))
        
        # --- 4. CRIAR COMENTÁRIOS ---
        self.stdout.write(self.style.NOTICE('Criando 150 comentários de teste...'))
        test_users = User.objects.filter(is_staff=False)
        all_questions = list(Questao.objects.all())
        for _ in range(150):
            Comentario.objects.create(
                questao=random.choice(all_questions),
                usuario=random.choice(test_users),
                conteudo=fake.paragraph(nb_sentences=2)
            )
        self.stdout.write(self.style.SUCCESS('-> 150 comentários criados.'))