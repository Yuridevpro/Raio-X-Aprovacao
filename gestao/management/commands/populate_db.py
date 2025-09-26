# gestao/management/commands/populate_db.py

from django.core.management.base import BaseCommand
from django.core import management

class Command(BaseCommand):
    help = 'Executa todos os scripts de população do banco de dados na ordem correta.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('===================================================='))
        self.stdout.write(self.style.SUCCESS('🚀 INICIANDO POPULAÇÃO COMPLETA DO BANCO DE DADOS 🚀'))
        self.stdout.write(self.style.SUCCESS('====================================================\n'))

        # A ordem de execução é crucial para garantir que as dependências
        # entre os modelos (chaves estrangeiras) sejam satisfeitas.

        # 1. Usuários: A base para todo o resto.
        self.stdout.write(self.style.NOTICE('\n[PASSO 1 de 5] Criando usuários de teste...'))
        management.call_command('create_test_users')

        # 2. Conteúdo Principal: Questões, Disciplinas, etc.
        self.stdout.write(self.style.NOTICE('\n[PASSO 2 de 5] Criando conteúdo de teste (Questões, Comentários)...'))
        management.call_command('create_test_content')

        # 3. Gamificação: Itens que podem ser recompensas.
        self.stdout.write(self.style.NOTICE('\n[PASSO 3 de 5] Criando elementos de gamificação (Conquistas, Recompensas)...'))
        management.call_command('create_test_gamification')
        
        # 4. Simulados: Utilizam as questões já criadas.
        self.stdout.write(self.style.NOTICE('\n[PASSO 4 de 5] Criando simulados de teste...'))
        management.call_command('create_test_simulados')
        
        # 5. Notificações: Baseado no conteúdo existente.
        self.stdout.write(self.style.NOTICE('\n[PASSO 5 de 5] Gerando notificações e denúncias de teste...'))
        management.call_command('create_test_reports')
        
        self.stdout.write(self.style.SUCCESS('\n===================================================='))
        self.stdout.write(self.style.SUCCESS('✅ POPULAÇÃO DO BANCO DE DADOS CONCLUÍDA! ✅'))
        self.stdout.write(self.style.SUCCESS('===================================================='))
        self.stdout.write(self.style.NOTICE('Execute `python manage.py runserver` para ver os resultados.'))