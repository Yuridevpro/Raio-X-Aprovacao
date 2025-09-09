# gestao/management/commands/create_test_notifications.py

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from django.db import IntegrityError

# Importa os modelos necessários
from questoes.models import Questao
from pratica.models import Notificacao # O modelo Notificacao está no app 'pratica'

class Command(BaseCommand):
    help = 'Cria notificações de teste, com usuários de teste reportando questões de teste.'

    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.NOTICE('Iniciando a criação de notificações de teste...'))

        # --- 1. LIMPAR NOTIFICAÇÕES ANTIGAS ---
        # Deleta apenas as notificações feitas por usuários de teste para não apagar reports reais.
        self.stdout.write(self.style.WARNING('Deletando notificações de teste antigas...'))
        count, _ = Notificacao.objects.filter(usuario_reportou__username__startswith='testuser').delete()
        self.stdout.write(self.style.SUCCESS(f'{count} notificações de teste antigas foram deletadas.'))

        # --- 2. BUSCAR USUÁRIOS E QUESTÕES DE TESTE ---
        test_users = list(User.objects.filter(username__startswith='testuser'))
        test_questions = list(Questao.objects.all()) # Pega todas as questões existentes

        if not test_users:
            self.stdout.write(self.style.ERROR('Nenhum usuário de teste (começando com "testuser") encontrado.'))
            self.stdout.write(self.style.ERROR('Execute "python manage.py create_test_users" primeiro. Abortando.'))
            return
        
        if not test_questions:
            self.stdout.write(self.style.ERROR('Nenhuma questão encontrada no banco de dados.'))
            self.stdout.write(self.style.ERROR('Execute "python manage.py create_test_questions" primeiro. Abortando.'))
            return

        # --- 3. CRIAR NOTIFICAÇÕES ALEATÓRIAS ---
        # Vamos tentar criar 30 notificações. Algumas podem falhar devido à constraint (mesmo usuário reportando a mesma questão)
        
        notificacoes_criadas = 0
        tentativas = 0
        max_notificacoes = 100 # Defina quantas notificações você quer criar

        self.stdout.write(self.style.NOTICE(f'Tentando criar até {max_notificacoes} notificações...'))

        while notificacoes_criadas < max_notificacoes and tentativas < 100: # O limite de tentativas evita um loop infinito
            tentativas += 1
            
            # Escolhe um usuário e uma questão aleatoriamente
            usuario_aleatorio = random.choice(test_users)
            questao_aleatoria = random.choice(test_questions)
            
            # Escolhe um tipo de erro e cria uma descrição aleatória
            tipo_erro_aleatorio = random.choice(Notificacao.TipoErro.choices)[0]
            descricao_aleatoria = fake.sentence(nb_words=random.randint(6, 12))

            try:
                # O método get_or_create é perfeito aqui. Ele tenta criar, mas se a notificação
                # já existir (mesmo usuário/questão), ele não faz nada e não levanta erro.
                # A sua constraint `unique_active_report_per_user_per_question` é respeitada.
                _, created = Notificacao.objects.get_or_create(
                    questao=questao_aleatoria,
                    usuario_reportou=usuario_aleatorio,
                    status=Notificacao.Status.PENDENTE, # Garante que estamos checando apenas pendentes
                    defaults={
                        'tipo_erro': tipo_erro_aleatorio,
                        'descricao': descricao_aleatoria,
                    }
                )

                if created:
                    notificacoes_criadas += 1
                    self.stdout.write('.', ending='')

            except IntegrityError:
                # Este bloco é um fallback caso get_or_create não pegue todos os casos
                # (embora ele deva pegar). Apenas continua para a próxima tentativa.
                continue

        self.stdout.write(self.style.SUCCESS(f'\n----------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS(f'{notificacoes_criadas} novas notificações de teste foram criadas com sucesso!'))
        self.stdout.write(self.style.SUCCESS(f'Vá para o painel de gestão para revisar as notificações pendentes.'))
        self.stdout.write(self.style.SUCCESS(f'----------------------------------------------------'))