# gestao/management/commands/age_item.py

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from questoes.models import Questao
from gestao.models import LogAtividade

class Command(BaseCommand):
    help = 'Envelhece a data de exclusão de um item na lixeira para fins de teste.'

    def add_arguments(self, parser):
        parser.add_argument('tipo', type=str, choices=['questao', 'log'], help='O tipo de item a ser envelhecido.')
        parser.add_argument('id', type=int, help='O ID do item a ser envelhecido.')
        parser.add_argument('--dias', type=int, default=31, help='Número de dias para envelhecer o item. Padrão: 31.')

    def handle(self, *args, **options):
        tipo = options['tipo']
        item_id = options['id']
        dias = options['dias']
        
        model_map = {
            'questao': Questao.all_objects,
            'log': LogAtividade.all_logs,
        }
        manager = model_map.get(tipo)
        
        try:
            item = manager.get(id=item_id)
        except Exception as e:
            raise CommandError(f'Item do tipo "{tipo}" com ID "{item_id}" não encontrado. Erro: {e}')

        if not item.is_deleted or not item.deleted_at:
            raise CommandError(f'O item "{tipo} #{item_id}" não está na lixeira.')

        nova_data = timezone.now() - timedelta(days=dias)
        item.deleted_at = nova_data
        item.save(update_fields=['deleted_at'])

        self.stdout.write(self.style.SUCCESS(
            f'Sucesso! O item "{tipo} #{item_id}" agora consta como deletado em: {nova_data.strftime("%d/%m/%Y %H:%M")}'
        ))