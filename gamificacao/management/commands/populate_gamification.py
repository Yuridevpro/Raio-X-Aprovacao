# gamificacao/management/commands/populate_gamification.py

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from faker import Faker

from questoes.models import Questao
from pratica.models import RespostaUsuario
from gamificacao.models import ProfileGamificacao, ProfileStreak, MetaDiariaUsuario
from gamificacao.services import processar_resposta_gamificacao
from simulados.models import Simulado, SessaoSimulado

class Command(BaseCommand):
    help = 'Popula o sistema com dados de gamificação de teste para múltiplos usuários.'

    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.NOTICE('Iniciando a população de dados de gamificação...'))

        # --- 1. BUSCAR DADOS DE TESTE ---
        test_users = list(User.objects.filter(username__startswith='testuser', is_staff=False, is_active=True))
        all_questions = list(Questao.objects.all())
        all_simulados = list(Simulado.objects.filter(is_oficial=True))

        if not test_users:
            self.stdout.write(self.style.ERROR('Nenhum usuário de teste (começando com "testuser") encontrado. Abortando.'))
            return
        
        if not all_questions:
            self.stdout.write(self.style.ERROR('Nenhuma questão encontrada no banco de dados. Abortando.'))
            return

        # --- 2. LIMPAR DADOS ANTIGOS ---
        self.stdout.write(self.style.WARNING('Limpando dados de gamificação e respostas antigas dos usuários de teste...'))
        user_ids = [user.id for user in test_users]
        RespostaUsuario.objects.filter(usuario_id__in=user_ids).delete()
        SessaoSimulado.objects.filter(usuario_id__in=user_ids).delete()
        ProfileGamificacao.objects.filter(user_profile__user_id__in=user_ids).update(level=1, xp=0, acertos_consecutivos=0)
        ProfileStreak.objects.filter(user_profile__user_id__in=user_ids).update(current_streak=0, max_streak=0, last_practice_date=None)
        MetaDiariaUsuario.objects.filter(user_profile__user_id__in=user_ids).delete()
        self.stdout.write(self.style.SUCCESS('Dados antigos limpos.'))

        # --- 3. SIMULAR ATIVIDADE DE RESPOSTAS ---
        total_respostas_simuladas = 200
        self.stdout.write(self.style.NOTICE(f'Simulando {total_respostas_simuladas} respostas de questões...'))
        
        with transaction.atomic():
            for i in range(total_respostas_simuladas):
                usuario_aleatorio = random.choice(test_users)
                questao_aleatoria = random.choice(all_questions)
                foi_correta = random.choices([True, False], weights=[0.7, 0.3], k=1)[0] # 70% de chance de acertar

                # Simula uma data de resposta nos últimos 30 dias para popular os rankings
                data_simulada = timezone.now() - timedelta(days=random.randint(0, 30))

                RespostaUsuario.objects.update_or_create(
                    usuario=usuario_aleatorio,
                    questao=questao_aleatoria,
                    defaults={
                        'alternativa_selecionada': questao_aleatoria.gabarito if foi_correta else 'X',
                        'foi_correta': foi_correta,
                        'data_resposta': data_simulada
                    }
                )
                
                # Simula a atualização do streak (lógica simplificada para o script)
                streak_data, _ = ProfileStreak.objects.get_or_create(user_profile=usuario_aleatorio.userprofile)
                if streak_data.last_practice_date != data_simulada.date():
                    streak_data.last_practice_date = data_simulada.date()
                    streak_data.current_streak +=1 # Lógica simplificada
                    if streak_data.current_streak > streak_data.max_streak:
                        streak_data.max_streak = streak_data.current_streak
                    streak_data.save()
                
                # Roda a lógica de gamificação completa
                processar_resposta_gamificacao(usuario_aleatorio.userprofile, foi_correta)
                
                if (i + 1) % 20 == 0:
                    self.stdout.write(self.style.SUCCESS(f'{i + 1}/{total_respostas_simuladas} respostas processadas...'))

        # --- 4. SIMULAR FINALIZAÇÃO DE SIMULADO PARA ALGUNS USUÁRIOS ---
        if all_simulados:
            self.stdout.write(self.style.NOTICE('Simulando a finalização de alguns simulados...'))
            usuarios_para_simulado = random.sample(test_users, k=min(len(test_users), 3)) # Pega até 3 usuários
            for user in usuarios_para_simulado:
                simulado_aleatorio = random.choice(all_simulados)
                # Cria uma sessão finalizada para disparar o signal
                SessaoSimulado.objects.create(
                    simulado=simulado_aleatorio,
                    usuario=user,
                    finalizado=True,
                    data_fim=timezone.now()
                )
                self.stdout.write(f"Simulado '{simulado_aleatorio.nome}' finalizado para o usuário '{user.username}'.")
        
        # --- 5. EXIBIR RESUMO E PRÓXIMOS PASSOS ---
        self.stdout.write(self.style.SUCCESS('\n----------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS('População de dados de gamificação concluída!'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------------------\n'))
        self.stdout.write(self.style.NOTICE('Ações realizadas:'))
        self.stdout.write('- Dados de gamificação antigos dos usuários de teste foram zerados.')
        self.stdout.write(f'- {total_respostas_simuladas} respostas foram simuladas e distribuídas aleatoriamente.')
        self.stdout.write('- Níveis, XP, streaks e conquistas foram calculados.\n')
        self.stdout.write(self.style.NOTICE('O que testar agora no front-end:'))
        self.stdout.write(self.style.SUCCESS('1. Acesse a página de Ranking: Você verá os usuários de teste populando os rankings Geral, Semanal e Mensal.'))
        self.stdout.write(self.style.SUCCESS('2. Clique nos nomes dos usuários no ranking: Você será levado aos seus perfis públicos.'))
        self.stdout.write(self.style.SUCCESS('3. Inspecione os perfis: Verifique as barras de XP, níveis, streaks e o Hall de Conquistas de cada um.'))
        self.stdout.write(self.style.SUCCESS('4. Faça login com uma das contas de teste: Responda a mais questões e veja os toasts de XP, level up e conquistas em tempo real.'))