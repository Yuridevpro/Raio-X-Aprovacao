# gestao/management/commands/create_test_notifications.py

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from django.db import IntegrityError

# Importa os modelos necessários
from questoes.models import Questao
from pratica.models import Notificacao, Comentario # Adicionado Comentario

class Command(BaseCommand):
    help = 'Cria notificações de teste para Questões e Comentários.'

    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.NOTICE('Iniciando a criação de notificações de teste...'))

        # --- 1. LIMPAR NOTIFICAÇÕES ANTIGAS ---
        self.stdout.write(self.style.WARNING('Deletando notificações de teste antigas...'))
        count, _ = Notificacao.objects.filter(usuario_reportou__username__startswith='testuser').delete()
        self.stdout.write(self.style.SUCCESS(f'{count} notificações de teste antigas foram deletadas.'))

        # --- 2. BUSCAR DADOS DE TESTE ---
        test_users = list(User.objects.filter(username__startswith='testuser'))
        test_questions = list(Questao.objects.all())
        test_comments = list(Comentario.objects.all())

        if not test_users:
            self.stdout.write(self.style.ERROR('Nenhum usuário de teste (começando com "testuser") encontrado. Abortando.'))
            return
        
        if not test_questions and not test_comments:
            self.stdout.write(self.style.ERROR('Nenhuma questão ou comentário encontrado no banco de dados para criar notificações. Abortando.'))
            return

        # --- 3. CRIAR NOTIFICAÇÕES ALEATÓRIAS ---
        notificacoes_criadas = 0
        tentativas = 0
        max_notificacoes = 100

        self.stdout.write(self.style.NOTICE(f'Tentando criar até {max_notificacoes} notificações...'))

        while notificacoes_criadas < max_notificacoes and tentativas < max_notificacoes * 2:
            tentativas += 1
            
            usuario_aleatorio = random.choice(test_users)
            
            # =======================================================================
            # INÍCIO DA CORREÇÃO: Lógica para escolher aleatoriamente entre Questão e Comentário
            # =======================================================================
            alvo_aleatorio = None
            tipo_erro_choices = []
            
            # Escolhe aleatoriamente se o alvo será uma questão ou um comentário
            if random.choice([True, False]) and test_questions:
                alvo_aleatorio = random.choice(test_questions)
                tipo_erro_choices = [c[0] for c in Notificacao.TipoErro.choices if not c[0].startswith('COMENTARIO')]
            elif test_comments:
                alvo_aleatorio = random.choice(test_comments)
                tipo_erro_choices = [c[0] for c in Notificacao.TipoErro.choices if c[0].startswith('COMENTARIO')]
            
            if not alvo_aleatorio or not tipo_erro_choices:
                continue # Pula se não houver alvo ou tipos de erro apropriados
            
            tipo_erro_aleatorio = random.choice(tipo_erro_choices)
            descricao_aleatoria = fake.sentence(nb_words=random.randint(6, 12))

            try:
                # O create agora usa o campo genérico `alvo`
                notificacao = Notificacao(
                    alvo=alvo_aleatorio,
                    usuario_reportou=usuario_aleatorio,
                    status=Notificacao.Status.PENDENTE,
                    tipo_erro=tipo_erro_aleatorio,
                    descricao=descricao_aleatoria
                )
                # Usamos .save() dentro de um try/except para capturar a IntegrityError
                # que é gerada pela `UniqueConstraint` do modelo.
                notificacao.save()
                notificacoes_criadas += 1
                self.stdout.write('.', ending='')

            except IntegrityError:
                # Isso acontece se o mesmo usuário tentar reportar o mesmo item duas vezes.
                # É um comportamento esperado e seguro, apenas continuamos para a próxima tentativa.
                continue
            # =======================================================================
            # FIM DA CORREÇÃO
            # =======================================================================

        self.stdout.write(self.style.SUCCESS(f'\n----------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS(f'{notificacoes_criadas} novas notificações de teste foram criadas com sucesso!'))
        self.stdout.write(self.style.SUCCESS(f'Vá para o painel de gestão para revisar as notificações pendentes.'))
        self.stdout.write(self.style.SUCCESS(f'----------------------------------------------------'))