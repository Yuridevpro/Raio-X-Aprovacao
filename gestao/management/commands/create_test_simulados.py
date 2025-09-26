# gestao/management/commands/create_test_simulados.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from simulados.models import Simulado, StatusSimulado, NivelDificuldade
from questoes.models import Questao
import random

class Command(BaseCommand):
    help = 'Cria simulados oficiais de teste com diferentes status e dificuldades.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Limpando e recriando simulados de teste...'))

        # --- LIMPEZA ---
        Simulado.objects.filter(nome__startswith='[TESTE]').delete()

        # --- CRIAÇÃO ---
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('Nenhum superusuário encontrado para ser o autor dos simulados. Abortando.'))
            return
            
        todas_as_questoes = list(Questao.objects.all())
        if len(todas_as_questoes) < 20:
            self.stdout.write(self.style.ERROR('São necessárias pelo menos 20 questões no banco para criar os simulados. Execute `populate_db` primeiro. Abortando.'))
            return

        # Simulado Ativo
        simulado_ativo = Simulado.objects.create(
            nome="[TESTE] Simulado Ativo de Constitucional",
            criado_por=admin_user, is_oficial=True, status=StatusSimulado.ATIVO,
            dificuldade=NivelDificuldade.MEDIO
        )
        simulado_ativo.questoes.set(random.sample(todas_as_questoes, k=15))
        
        # Simulado Em Breve
        simulado_embreve = Simulado.objects.create(
            nome="[TESTE] Simulado Em Breve de Português",
            criado_por=admin_user, is_oficial=True, status=StatusSimulado.EM_BREVE,
            dificuldade=NivelDificuldade.DIFICIL
        )
        simulado_embreve.questoes.set(random.sample(todas_as_questoes, k=20))
        
        # Simulado Arquivado
        simulado_arquivado = Simulado.objects.create(
            nome="[TESTE] Simulado Antigo Arquivado",
            criado_por=admin_user, is_oficial=True, status=StatusSimulado.ARQUIVADO,
            dificuldade=NivelDificuldade.FACIL
        )
        simulado_arquivado.questoes.set(random.sample(todas_as_questoes, k=10))

        self.stdout.write(self.style.SUCCESS('-> 3 simulados oficiais de teste foram criados.'))