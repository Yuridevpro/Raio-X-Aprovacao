# gestao/management/commands/create_test_users.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from usuarios.models import UserProfile 
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Limpa e cria uma base diversificada de usuários de teste (Comuns, Staff, Superuser).'

    def handle(self, *args, **options):
        fake = Faker('pt_BR')
        
        # --- 1. DELETAR USUÁRIOS DE TESTE ANTIGOS ---
        self.stdout.write(self.style.WARNING('Limpando usuários de teste antigos...'))
        old_test_users = User.objects.filter(username__startswith='test_')
        count, _ = old_test_users.delete()
        self.stdout.write(self.style.SUCCESS(f'{count} usuários de teste antigos foram deletados.'))

        # --- 2. CRIAR USUÁRIOS DE TESTE ---
        self.stdout.write(self.style.NOTICE('Criando uma nova base de usuários de teste...'))
        
        # SUPERUSUÁRIOS
        for i in range(3):
            username = f'test_su_{i+1}'
            user = User.objects.create_superuser(username, f'{username}@example.com', 'password123')
            UserProfile.objects.create(user=user, nome=fake.first_name(), sobrenome=fake.last_name())
        self.stdout.write(self.style.SUCCESS('-> 3 Superusuários criados (ex: test_su_1)'))

        # EQUIPE (STAFF)
        for i in range(5):
            username = f'test_staff_{i+1}'
            user = User.objects.create_user(username, f'{username}@example.com', 'password123', is_staff=True)
            UserProfile.objects.create(user=user, nome=fake.first_name(), sobrenome=fake.last_name())
        self.stdout.write(self.style.SUCCESS('-> 5 Membros da Equipe criados (ex: test_staff_1)'))

        # USUÁRIOS COMUNS
        for i in range(25):
            username = f'test_user_{i+1}'
            user = User.objects.create_user(username, f'{username}@example.com', 'password123')
            UserProfile.objects.create(user=user, nome=fake.first_name(), sobrenome=fake.last_name())
        self.stdout.write(self.style.SUCCESS('-> 25 Usuários Comuns criados (ex: test_user_1)'))
        
        self.stdout.write(self.style.SUCCESS('----------------------------------------------------'))
        self.stdout.write(self.style.NOTICE('A senha para todos os usuários é: password123'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------------------'))