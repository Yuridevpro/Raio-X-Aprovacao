# gestao/management/commands/create_test_reports.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from django.db import IntegrityError
from questoes.models import Questao
from pratica.models import Notificacao, Comentario
import random

class Command(BaseCommand):
    help = 'Gera notificações de teste (denúncias) para Questões e Comentários.'

    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.NOTICE('Iniciando a criação de denúncias de teste...'))

        # --- 1. LIMPAR NOTIFICAÇÕES ANTIGAS ---
        self.stdout.write(self.style.WARNING('Limpando denúncias de teste antigas...'))
        count, _ = Notificacao.objects.filter(usuario_reportou__username__startswith='test_').delete()
        self.stdout.write(self.style.SUCCESS(f'{count} denúncias antigas foram deletadas.'))

        # --- 2. BUSCAR DADOS ---
        test_users = list(User.objects.filter(username__startswith='test_'))
        test_questions = list(Questao.objects.all())
        test_comments = list(Comentario.objects.all())

        if not test_users or (not test_questions and not test_comments):
            self.stdout.write(self.style.ERROR('Faltam dados para criar denúncias (usuários, questões ou comentários). Execute `populate_db`. Abortando.'))
            return

        # --- 3. CRIAR NOTIFICAÇÕES ---
        reports_criados = 0
        for i in range(50): # Tenta criar 50 denúncias
            reportador = random.choice(test_users)
            alvo = None
            tipo_erro_choices = []

            if random.choice([True, False]) and test_questions:
                alvo = random.choice(test_questions)
                tipo_erro_choices = [c[0] for c in Notificacao.TipoErro.choices if not c[0].startswith('COMENTARIO')]
            elif test_comments:
                alvo = random.choice(test_comments)
                tipo_erro_choices = [c[0] for c in Notificacao.TipoErro.choices if c[0].startswith('COMENTARIO')]
            
            if not alvo or not tipo_erro_choices:
                continue

            try:
                Notificacao.objects.create(
                    alvo=alvo,
                    usuario_reportou=reportador,
                    tipo_erro=random.choice(tipo_erro_choices),
                    descricao=fake.sentence(nb_words=8)
                )
                reports_criados += 1
            except IntegrityError:
                continue
        
        self.stdout.write(self.style.SUCCESS(f'-> {reports_criados} novas denúncias de teste foram criadas.'))