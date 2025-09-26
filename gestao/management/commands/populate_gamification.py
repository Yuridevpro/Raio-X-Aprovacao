# gamificacao/management/commands/populate_gamification.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
import random
from datetime import timedelta
from django.utils import timezone

# Importações dos modelos e serviços necessários
from questoes.models import Questao
from pratica.models import RespostaUsuario
from usuarios.models import UserProfile
from gamificacao.models import ProfileGamificacao, MetaDiariaUsuario, ProfileStreak
from gamificacao.services import processar_resposta_gamificacao

class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de gamificação realistas para usuários de teste.'

    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.NOTICE('Iniciando a população de dados de gamificação...'))

        # --- 1. BUSCAR DADOS NECESSÁRIOS ---
        test_users = list(User.objects.filter(username__startswith='test_'))
        all_questions = list(Questao.objects.all())

        if not test_users or not all_questions:
            self.stdout.write(self.style.ERROR('Faltam dados base (usuários ou questões de teste). Execute `populate_db` primeiro. Abortando.'))
            return

        # --- 2. LIMPAR DADOS ANTIGOS ---
        self.stdout.write(self.style.WARNING('Limpando dados de gamificação e respostas antigas dos usuários de teste...'))
        ProfileGamificacao.objects.filter(user_profile__user__in=test_users).delete()
        ProfileStreak.objects.filter(user_profile__user__in=test_users).delete()
        MetaDiariaUsuario.objects.filter(user_profile__user__in=test_users).delete()
        RespostaUsuario.objects.filter(usuario__in=test_users).delete()
        self.stdout.write(self.style.SUCCESS('Dados antigos limpos.'))

        # --- 3. SIMULAR RESPOSTAS E ATIVIDADE ---
        self.stdout.write(self.style.NOTICE('Simulando 500 respostas de questões para gerar dados...'))
        
        for i in range(500):
            usuario_aleatorio = random.choice(test_users)
            questao_aleatoria = random.choice(all_questions)
            
            # 1. Simula se o usuário acertou ou errou
            acertou = random.random() < 0.65  # 65% de chance de acerto
            
            # 2. Escolhe uma alternativa. Se acertou, pega o gabarito. Se errou, pega uma diferente.
            if acertou:
                alternativa_escolhida = questao_aleatoria.gabarito
            else:
                opcoes_erradas = [letra for letra in 'ABCDE' if letra != questao_aleatoria.gabarito and letra in questao_aleatoria.get_alternativas_dict()]
                if not opcoes_erradas:
                    continue
                alternativa_escolhida = random.choice(opcoes_erradas)

            # 3. Chama a função de serviço com os argumentos NOMEADOS e corretos
            processar_resposta_gamificacao(
                user=usuario_aleatorio,
                questao=questao_aleatoria,
                alternativa_selecionada=alternativa_escolhida
            )

            # Simula que as respostas ocorreram em dias diferentes para gerar streaks
            if i % 10 == 0: # a cada 10 respostas, simula um dia diferente
                try:
                    profile_streak, _ = ProfileStreak.objects.get_or_create(user_profile=usuario_aleatorio.userprofile)
                    dias_atras = random.randint(1, 30)
                    profile_streak.last_practice_date = timezone.now().date() - timedelta(days=dias_atras)
                    profile_streak.save()
                except UserProfile.DoesNotExist:
                    continue

            if (i + 1) % 50 == 0:
                self.stdout.write(f'  -> {i + 1}/500 respostas simuladas...')

        self.stdout.write(self.style.SUCCESS('\n----------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS('Dados de gamificação e respostas populados com sucesso!'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------------------'))