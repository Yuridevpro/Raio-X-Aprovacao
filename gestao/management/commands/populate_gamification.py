# gamificacao/management/commands/populate_gamification.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
import random
from datetime import date, timedelta
from django.utils import timezone
from django.db import transaction
from datetime import datetime


from questoes.models import Questao
from pratica.models import RespostaUsuario
from usuarios.models import UserProfile
from gamificacao.models import RankingSemanal, RankingMensal

class Command(BaseCommand):
    help = 'Popula o banco de dados com respostas de usuários em períodos de tempo específicos para testar os rankings.'

    @transaction.atomic
    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.NOTICE('Iniciando a população de dados para o ranking...'))

        # --- 1. BUSCAR DADOS NECESSÁRIOS ---
        users = list(User.objects.filter(is_staff=False, is_active=True))
        all_questions = list(Questao.objects.all())

        if not users or not all_questions:
            self.stdout.write(self.style.ERROR('Faltam usuários ou questões. Abortando.'))
            return

        # --- 2. LIMPAR DADOS ANTIGOS ---
        self.stdout.write(self.style.WARNING('Limpando dados de respostas e rankings antigos...'))
        RespostaUsuario.objects.all().delete()
        RankingSemanal.objects.all().delete()
        RankingMensal.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Dados antigos limpos.'))

        # --- 3. SIMULAR RESPOSTAS EM PERÍODOS DE TEMPO ESTRUTURADOS ---
        hoje = timezone.now()
        
        # Períodos de tempo para simulação
        periodos = {
            "mes_retrasado": (hoje.date() - timedelta(days=60), "Mês Retrasado"),
            "mes_passado": (hoje.date() - timedelta(days=30), "Mês Passado"),
            "semana_retrasada": (hoje.date() - timedelta(days=14), "Semana Retrasada"),
            "semana_passada": (hoje.date() - timedelta(days=7), "Semana Passada"),
            "semana_atual": (hoje.date(), "Semana Atual"),
        }

        for chave_periodo, (data_base, nome_periodo) in periodos.items():
            self.stdout.write(self.style.NOTICE(f'Simulando respostas para o período: {nome_periodo}'))
            
            # Seleciona um subconjunto de usuários para participar neste período
            participantes = random.sample(users, k=min(len(users), 15))
            
            for usuario in participantes:
                num_respostas = random.randint(5, 20)
                for _ in range(num_respostas):
                    questao = random.choice(all_questions)
                    acertou = random.random() < 0.7  # 70% de chance de acerto
                    alternativa = questao.gabarito if acertou else random.choice([k for k in 'ABCDE' if k != questao.gabarito])
                    
                    # Simula uma data de resposta dentro do período
                    dia_aleatorio = data_base - timedelta(days=random.randint(0, 5))
                    
                    RespostaUsuario.objects.update_or_create(
                        usuario=usuario,
                        questao=questao,
                        defaults={
                            'alternativa_selecionada': alternativa,
                            'foi_correta': acertou,
                            'data_resposta': timezone.make_aware(datetime.combine(dia_aleatorio, timezone.now().time()))
                        }
                    )
            self.stdout.write(f'  -> {len(participantes)} usuários participaram.')

        self.stdout.write(self.style.SUCCESS('\n----------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS('Dados de respostas populados com sucesso!'))
        self.stdout.write(self.style.NOTICE('Execute o servidor e acesse a página /ranking para gerar os rankings semanais e mensais.'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------------------'))