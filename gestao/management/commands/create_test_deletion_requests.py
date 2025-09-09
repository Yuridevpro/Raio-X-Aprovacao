# gestao/management/commands/create_test_deletion_requests.py

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker

# Importa o modelo de Solicitação do app 'gestao'
from gestao.models import SolicitacaoExclusao

class Command(BaseCommand):
    help = 'Cria 30 solicitações de exclusão de teste pendentes.'

    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.NOTICE('Iniciando a criação de solicitações de exclusão...'))

        # --- 1. LIMPAR SOLICITAÇÕES ANTIGAS ---
        self.stdout.write(self.style.WARNING('Deletando solicitações de teste antigas...'))
        # Deleta apenas solicitações feitas por usuários de teste
        count, _ = SolicitacaoExclusao.objects.filter(solicitado_por__username__startswith='testuser').delete()
        self.stdout.write(self.style.SUCCESS(f'{count} solicitações antigas foram deletadas.'))

        # --- 2. PREPARAR OS GRUPOS DE USUÁRIOS ---
        
        # Primeiro, garantir que alguns usuários de teste sejam staff
        test_users_to_promote = User.objects.filter(
            username__startswith='testuser', 
            is_staff=False, 
            is_superuser=False
        )[:5] # Vamos promover os 5 primeiros que encontrarmos

        for user in test_users_to_promote:
            user.is_staff = True
            user.save()
        
        # Agora, separamos os usuários em dois grupos
        staff_requesters = list(User.objects.filter(
            username__startswith='testuser', 
            is_staff=True, 
            is_superuser=False
        ))
        
        common_users_targets = list(User.objects.filter(
            username__startswith='testuser',
            is_staff=False,
            is_superuser=False
        ))

        if not staff_requesters:
            self.stdout.write(self.style.ERROR('Nenhum usuário de teste com permissão de staff encontrado.'))
            self.stdout.write(self.style.ERROR('Execute "python manage.py create_test_users" e tente novamente. Abortando.'))
            return
        
        if not common_users_targets:
            self.stdout.write(self.style.ERROR('Nenhum usuário comum de teste encontrado para ser o alvo das solicitações.'))
            self.stdout.write(self.style.ERROR('Execute "python manage.py create_test_users" primeiro. Abortando.'))
            return

        # --- 3. CRIAR 30 SOLICITAÇÕES ALEATÓRIAS ---
        
        solicitacoes_criadas = 0
        tentativas = 0
        max_solicitacoes = 30

        self.stdout.write(self.style.NOTICE(f'Criando até {max_solicitacoes} solicitações...'))

        while solicitacoes_criadas < max_solicitacoes and tentativas < 150:
            tentativas += 1
            
            solicitante = random.choice(staff_requesters)
            alvo = random.choice(common_users_targets)
            
            # Gera os motivos
            motivo_predefinido = random.choice([
                'Violação dos Termos de Serviço', 
                'Conduta Inadequada / Abusiva',
                'Conta Inativa por Longo Período'
            ])
            justificativa_detalhada = fake.paragraph(nb_sentences=2)
            motivo_completo = f"Motivo: {motivo_predefinido}\n\nJustificativa: {justificativa_detalhada}"

            # Usa get_or_create para evitar criar solicitações duplicadas (mesmo alvo, mesmo solicitante)
            _, created = SolicitacaoExclusao.objects.get_or_create(
                usuario_a_ser_excluido=alvo,
                solicitado_por=solicitante,
                status=SolicitacaoExclusao.Status.PENDENTE,
                defaults={'motivo': motivo_completo}
            )

            if created:
                solicitacoes_criadas += 1
                self.stdout.write('.', ending='')
        
        self.stdout.write(self.style.SUCCESS(f'\n----------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS(f'{solicitacoes_criadas} novas solicitações de exclusão foram criadas.'))
        self.stdout.write(self.style.SUCCESS(f'Vá para o dashboard para revisar as solicitações.'))
        self.stdout.write(self.style.SUCCESS(f'----------------------------------------------------'))