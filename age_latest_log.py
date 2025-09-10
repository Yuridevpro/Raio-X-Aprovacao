# age_latest_log.py

import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

# --- Bloco Essencial para Carregar o Django ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qconcurso.settings')
django.setup()
# --- Fim do Bloco Essencial ---

# Agora que o Django está carregado, podemos importar os modelos
from gestao.models import LogAtividade

def make_latest_log_old():
    """
    Encontra o registro de log mais recente e altera sua data de criação
    para 100 dias no passado, tornando-o elegível para arquivamento.
    """
    print("--- INICIANDO SCRIPT PARA ENVELHECER O ÚLTIMO LOG ---")

    # 1. Encontra o log mais recente que ainda não foi arquivado
    log_recente = LogAtividade.objects.filter(is_archived=False).order_by('-id').first()

    if not log_recente:
        print("\n❌ AVISO: Nenhum log ativo foi encontrado no banco de dados.")
        print("   Por favor, execute alguma ação no painel de gestão para criar um log primeiro.")
        print("\n--- SCRIPT FINALIZADO SEM ALTERAÇÕES ---")
        return

    print(f"\n[INFO] Log encontrado: ID {log_recente.id}, criado em {log_recente.data_criacao.strftime('%d/%m/%Y %H:%M')}")

    # 2. Calcula a nova data (100 dias atrás)
    nova_data = timezone.now() - timedelta(days=100)

    # 3. Atualiza o registro no banco de dados
    try:
        log_recente.data_criacao = nova_data
        log_recente.save(update_fields=['data_criacao'])
        print(f"\n✅ SUCESSO! O log ID {log_recente.id} foi atualizado.")
        print(f"   Nova data de criação: {nova_data.strftime('%d/%m/%Y %H:%M')}")
        print("\n   Agora você pode testar a funcionalidade de 'Executar Arquivamento' na sua aplicação.")

    except Exception as e:
        print(f"\n❌ ERRO: Ocorreu um problema ao tentar salvar a alteração no banco de dados.")
        print(f"   Mensagem: {repr(e)}")

    print("\n--- SCRIPT FINALIZADO ---")


if __name__ == "__main__":
    make_latest_log_old()