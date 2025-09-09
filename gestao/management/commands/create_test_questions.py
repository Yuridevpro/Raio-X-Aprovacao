# gestao/management/commands/create_test_questions.py

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from questoes.models import Questao, Disciplina, Assunto, Banca, Instituicao

class Command(BaseCommand):
    help = 'Limpa questões de teste antigas e cria 50 novas questões para testes.'

    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        
        self.stdout.write(self.style.NOTICE('Iniciando a criação de 50 questões de teste...'))

        # --- 1. BUSCAR OU CRIAR OS DADOS RELACIONADOS EXISTENTES ---
        # Usamos os nomes exatos do seu sistema para garantir compatibilidade.
        
        # Garante que um usuário admin exista para ser o criador
        admin_user, created = User.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True})
        if created:
            admin_user.set_password('admin')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Usuário "admin" de teste criado.'))

        # Disciplinas
        disciplina_mat, _ = Disciplina.objects.get_or_create(nome='matematica')
        disciplina_port, _ = Disciplina.objects.get_or_create(nome='portugues')
        disciplina_banco, _ = Disciplina.objects.get_or_create(nome='Conhecimentos Bancários')
        
        # Bancas
        banca_cesgranrio, _ = Banca.objects.get_or_create(nome='Cesgranrio')
        
        # Instituições
        inst_bb, _ = Instituicao.objects.get_or_create(nome='banco do brasil')

        # Assuntos (vinculados às suas respectivas disciplinas)
        assunto_conj, _ = Assunto.objects.get_or_create(disciplina=disciplina_mat, nome='conjuntos')
        assunto_garantias, _ = Assunto.objects.get_or_create(disciplina=disciplina_banco, nome='Garantias do Sistema Financeiro Nacional')
        assunto_wwwee, _ = Assunto.objects.get_or_create(disciplina=disciplina_port, nome='wwwee')

        # Prepara listas para seleção aleatória
        disciplinas = [disciplina_mat, disciplina_port, disciplina_banco]
        bancas = [banca_cesgranrio]
        instituicoes = [inst_bb]
        assuntos = [assunto_conj, assunto_garantias, assunto_wwwee]

        # --- 2. DELETAR QUESTÕES DE TESTE ANTIGAS ---
        # Para evitar acúmulo de dados, deletamos questões criadas pelo admin de teste.
        self.stdout.write(self.style.WARNING('Deletando questões de teste antigas criadas pelo usuário "admin"...'))
        count, _ = Questao.objects.filter(criada_por=admin_user).delete()
        self.stdout.write(self.style.SUCCESS(f'{count} questões de teste antigas foram deletadas.'))
        
        self.stdout.write(self.style.NOTICE('Criando 50 novas questões...'))
        
        # --- 3. CRIAR AS 50 NOVAS QUESTÕES ---
        for i in range(50):
            disciplina_escolhida = random.choice(disciplinas)
            
            # Filtra os assuntos para que correspondam à disciplina escolhida
            assuntos_da_disciplina = [a for a in assuntos if a.disciplina == disciplina_escolhida]
            
            # Se por acaso uma disciplina não tiver assunto, pula para a próxima iteração
            if not assuntos_da_disciplina:
                continue

            # Seleciona dados aleatórios das nossas listas
            assunto_escolhido = random.choice(assuntos_da_disciplina)
            banca_escolhida = random.choice(bancas)
            instituicao_escolhida = random.choice(instituicoes)
            ano_escolhido = random.randint(2022, 2025)
            gabarito_letra = random.choice(['A', 'B', 'C', 'D', 'E'])
            
            # Gera alternativas com o Faker
            alternativas_dict = {
                letra: fake.sentence(nb_words=random.randint(8, 20))
                for letra in ['A', 'B', 'C', 'D', 'E']
            }

            # Cria a instância da Questao no banco de dados
            Questao.objects.create(
                disciplina=disciplina_escolhida,
                assunto=assunto_escolhido,
                banca=banca_escolhida,
                instituicao=instituicao_escolhida,
                ano=ano_escolhido,
                enunciado=f"({disciplina_escolhida.nome}) {fake.paragraph(nb_sentences=random.randint(2, 4))}",
                alternativas=alternativas_dict,
                gabarito=gabarito_letra,
                explicacao=fake.paragraph(nb_sentences=random.randint(2, 3)),
                criada_por=admin_user,
                is_inedita=random.choice([True, False]) # Aleatoriza se a questão é inédita ou não
            )
            self.stdout.write('.', ending='')

        self.stdout.write(self.style.SUCCESS('\n----------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS('50 novas questões de teste foram criadas com sucesso!'))
        self.stdout.write(self.style.SUCCESS('Execute `python manage.py runserver` e verifique o painel de gestão.'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------------------'))