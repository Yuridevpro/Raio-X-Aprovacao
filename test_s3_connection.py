# test_s3_connection.py

import os
import sys
import django
from django.core.files.base import ContentFile
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# --- Bloco Essencial para Carregar o Django ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qconcurso.settings')
django.setup()
# --- Fim do Bloco Essencial ---

# Agora que o Django está carregado, podemos importar nossos modelos
from questoes.models import Questao

def test_media_bucket():
    """
    Executa um teste de upload para o BUCKET DE MÍDIA (imagens, etc.)
    usando o sistema de armazenamento padrão do Django.
    """
    print("--- INICIANDO TESTE DO BUCKET DE MÍDIA ---")
    
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')

    if not bucket_name or not access_key:
        print("\n❌ ERRO: Variável 'AWS_STORAGE_BUCKET_NAME' não encontrada no seu .env.")
        return

    print(f"\n[INFO] Bucket de Mídia: '{bucket_name}'")
    
    questao_teste = Questao.objects.order_by('?').first()
    if not questao_teste:
        print("\n❌ AVISO: Nenhuma questão encontrada no DB. Pulando teste do bucket de mídia.")
        return

    test_file = ContentFile(b'Teste de conexao com o bucket de midia.', name='teste_conexao_media.txt')

    try:
        # Esta linha usa o storage configurado no modelo da Questão
        questao_teste.imagem_enunciado.save(test_file.name, test_file, save=True)
        print(f"\n✅ SUCESSO! A conexão com o bucket de mídia '{bucket_name}' está funcionando.")
        print(f"   URL do arquivo: {questao_teste.imagem_enunciado.url}")

    except Exception as e:
        print(f"\n❌ ERRO! A conexão com o bucket de mídia '{bucket_name}' FALHOU.")
        print(f"   Mensagem: {repr(e)}")
        print("   Verifique suas credenciais (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) e permissões (PutObject).")

def test_log_archive_bucket():
    """
    Executa um teste de upload para o BUCKET DE ARQUIVAMENTO DE LOGS
    usando o boto3 diretamente, da mesma forma que a função de arquivamento.
    """
    print("--- INICIANDO TESTE DO BUCKET DE ARQUIVAMENTO DE LOGS ---")

    bucket_name = os.getenv('AWS_LOG_ARCHIVE_BUCKET_NAME')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_S3_REGION_NAME')

    if not bucket_name:
        print("\n❌ ERRO: Variável 'AWS_LOG_ARCHIVE_BUCKET_NAME' não encontrada no seu .env.")
        return
    if not all([access_key, secret_key, region]):
        print("\n❌ ERRO: Credenciais ou região da AWS não encontradas no seu .env.")
        return

    print(f"\n[INFO] Bucket de Logs: '{bucket_name}'")

    try:
        s3_client = boto3.client('s3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        file_content = b'Teste de upload para o bucket de arquivamento de logs.'
        file_name = 'teste_conexao_logs.txt'

        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=file_content
        )
        
        print(f"\n✅ SUCESSO! A conexão com o bucket de logs '{bucket_name}' está funcionando.")
        print(f"   Verifique o arquivo '{file_name}' dentro do bucket no console da AWS.")

    except (NoCredentialsError, ClientError) as e:
        print(f"\n❌ ERRO! A conexão com o bucket de logs '{bucket_name}' FALHOU.")
        print(f"   Mensagem: {repr(e)}")
        print("   Verifique se o nome do bucket está correto e se as credenciais têm permissão (PutObject).")
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO! A conexão com o bucket de logs '{bucket_name}' FALHOU.")
        print(f"   Mensagem: {repr(e)}")


if __name__ == "__main__":
    print("==================================================")
    test_media_bucket()
    print("\n==================================================")
    test_log_archive_bucket()
    print("\n==================================================")
    print("Todos os testes de conexão com o S3 foram concluídos.")