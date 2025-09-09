# gestao/management/commands/create_test_users.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
# IMPORTANTE: Importe seu modelo UserProfile. Ajuste o caminho se necessário.
# Se o seu modelo de perfil está no app 'usuarios', o import abaixo está correto.
from usuarios.models import UserProfile 
import random

class Command(BaseCommand):
    help = 'Deleta usuários de teste antigos e cria 20 novos usuários para testes.'

    def handle(self, *args, **options):
        # --- 1. DELETAR USUÁRIOS DE TESTE ANTIGOS ---
        # Procura por usuários cujo nome começa com 'testuser' e que NÃO são superusuários.
        self.stdout.write(self.style.WARNING('Deletando usuários de teste antigos...'))
        
        old_test_users = User.objects.filter(
            username__startswith='testuser', 
            is_superuser=False
        )
        count, _ = old_test_users.delete()
        
        self.stdout.write(self.style.SUCCESS(f'{count} usuários de teste antigos foram deletados.'))

        # --- 2. CRIAR NOVOS USUÁRIOS DE TESTE ---
        self.stdout.write(self.style.NOTICE('Criando 20 novos usuários de teste...'))
        
        first_names = ["Ana", "Bruno", "Carla", "Daniel", "Elisa", "Fernando", "Gabriela", "Hugo"]
        last_names = ["Silva", "Souza", "Costa", "Santos", "Oliveira", "Pereira", "Rodrigues", "Almeida"]

        for i in range(20):
            # Gera dados aleatórios simples
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f'testuser{i + 1}'
            email = f'testuser{i+1}@example.com'
            password = 'password123'

            # Cria o objeto User. Usamos create_user para garantir que a senha seja hasheada.
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Cria o UserProfile relacionado, que é crucial para o seu sistema.
            UserProfile.objects.create(
                user=user,
                nome=f'{first_name} {last_name}'
            )

        self.stdout.write(self.style.SUCCESS('----------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS('20 novos usuários de teste criados com sucesso!'))
        self.stdout.write(self.style.SUCCESS('Usuários criados: de testuser1 a testuser20'))
        self.stdout.write(self.style.SUCCESS('A senha para todos é: password123'))
        self.stdout.write(self.style.SUCCESS('----------------------------------------------------'))