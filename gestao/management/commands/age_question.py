# gestao/management/commands/age_question.py

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from questoes.models import Questao

class Command(BaseCommand):
    help = 'Envelhece a data de exclusão de uma questão na lixeira para fins de teste.'

    def add_arguments(self, parser):
        # Argumento obrigatório: o código da questão (ex: Q123)
        parser.add_argument('codigo_questao', type=str, help='O código da questão a ser envelhecida (ex: Q123).')
        
        # Argumento opcional: o número de dias
        parser.add_argument(
            '--dias',
            type=int,
            default=30, # O padrão é 30 dias, garantindo que o teste passe
            help='O número de dias para "envelhecer" a questão. Padrão: 30.'
        )

    def handle(self, *args, **options):
        codigo_questao = options['codigo_questao']
        dias = options['dias']

        try:
            # Usamos `all_objects` para encontrar a questão mesmo que esteja na lixeira
            questao = Questao.all_objects.get(codigo__iexact=codigo_questao)
        except Questao.DoesNotExist:
            raise CommandError(f'Questão com código "{codigo_questao}" não foi encontrada.')

        # Verifica se a questão já está na lixeira
        if not questao.is_deleted or not questao.deleted_at:
            raise CommandError(f'A questão "{codigo_questao}" não está na lixeira. Mova-a para a lixeira primeiro.')

        # Calcula a nova data de exclusão "envelhecida"
        nova_data = timezone.now() - timedelta(days=dias)
        
        # Salva a nova data no banco de dados
        questao.deleted_at = nova_data
        questao.save(update_fields=['deleted_at'])

        # Exibe uma mensagem de sucesso no terminal
        self.stdout.write(self.style.SUCCESS(
            f'Sucesso! A questão "{codigo_questao}" agora consta como deletada em: {nova_data.strftime("%d/%m/%Y %H:%M")}'
        ))
        self.stdout.write(self.style.NOTICE(
            'Recarregue a página da lixeira no navegador para ver a mudança no botão de exclusão permanente.'
        ))