# test_s3_connection.py

import os
import django
from django.core.files.base import ContentFile
import sys

# Adiciona o diretório raiz do projeto ao path do Python
# para que o script encontre o módulo de settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- Bloco Essencial para Carregar o Django ---
# Define qual arquivo de settings o Django deve usar.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qconcurso.settings')
# Carrega as configurações e prepara o ambiente do Django.
django.setup()
# --- Fim do Bloco Essencial ---


# Agora que o Django está carregado, podemos importar nossos modelos
from questoes.models import Questao

def run_s3_test():
    """
    Executa um teste de upload para o Amazon S3 usando as configurações do projeto Django.
    """
    print("--- INICIANDO TESTE DE CONEXÃO COM O AMAZON S3 ---")

    # 1. Verifica se as variáveis de ambiente essenciais foram carregadas
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')

    if not bucket_name or not access_key:
        print("\n❌ ERRO: Variáveis de ambiente da AWS não encontradas.")
        print("   Verifique se seu arquivo .env está na raiz do projeto e contém:")
        print("   - AWS_STORAGE_BUCKET_NAME")
        print("   - AWS_ACCESS_KEY_ID")
        print("   - AWS_SECRET_ACCESS_KEY")
        print("   - AWS_S3_REGION_NAME")
        return # Encerra o script

    print(f"\n[INFO] Tentando conectar ao bucket: '{bucket_name}'")
    print(f"[INFO] Usando a chave de acesso que começa com: '{access_key[:5]}...'")

    # 2. Pega uma instância de um modelo para usar no teste
    questao_teste = Questao.objects.order_by('?').first() # Pega uma questão aleatória

    if not questao_teste:
        print("\n❌ ERRO: Nenhuma questão encontrada no banco de dados.")
        print("   Por favor, crie pelo menos uma questão no seu sistema antes de rodar o teste.")
        return

    print(f"[INFO] Usando a questão com ID {questao_teste.id} para o teste.")

    # 3. Cria um arquivo de teste em memória
    file_content = b'Este eh um arquivo de teste automatico de conexao com o S3.'
    test_file = ContentFile(file_content, name='teste_de_conexao.txt')

    # 4. Tenta salvar o arquivo, o que acionará o upload para o S3
    try:
        # A linha abaixo é a que efetivamente faz o upload para o S3
        questao_teste.imagem_enunciado.save(test_file.name, test_file)

        print("\n✅ SUCESSO! O arquivo foi salvo no S3.")
        print(f"   Verifique seu bucket '{bucket_name}' na pasta 'media/'.")
        print(f"   URL pública do arquivo gerado: {questao_teste.imagem_enunciado.url}")

    except Exception as e:
        print(f"\n❌ ERRO! A conexão com o S3 falhou.")
        print("   --------------------------------------------------")
        print("   Mensagem de erro detalhada:")
        print(f"   {repr(e)}")
        print("   --------------------------------------------------")
        print("\n   Possíveis causas:")
        print("   - 'AccessDenied': Suas chaves não têm permissão para escrever (PutObject) no bucket.")
        print("   - 'NoCredentialsError': O `boto3` não encontrou as credenciais; verifique seu `.env`.")
        print("   - 'SignatureDoesNotMatch': A Chave Secreta (SECRET_KEY) está incorreta.")
        print("   - 'NoSuchBucket': O nome do bucket está incorreto ou ele não existe na região especificada.")

    print("\n--- TESTE FINALIZADO ---")

if __name__ == "__main__":
    run_s3_test()