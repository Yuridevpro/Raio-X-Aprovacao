# gestao/utils.py

import boto3
import os
import json
from datetime import datetime, timedelta
from django.utils import timezone
from .models import LogAtividade
from botocore.exceptions import NoCredentialsError, ClientError
from .models import LogAtividade
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

def arquivar_logs_antigos_no_s3():
    """
    Busca logs com mais de 90 dias, os exporta para um arquivo JSON,
    envia para um bucket S3 de arquivamento e os marca como arquivados.
    """
    bucket_name = os.getenv('AWS_LOG_ARCHIVE_BUCKET_NAME')
    if not bucket_name:
        return False, "A variável de ambiente 'AWS_LOG_ARCHIVE_BUCKET_NAME' não está configurada."

    # 1. Encontrar logs com mais de 90 dias que não foram arquivados
    ninety_days_ago = timezone.now() - timedelta(days=90)
    logs_para_arquivar = LogAtividade.objects.filter(
        data_criacao__lt=ninety_days_ago,
        is_archived=False
    )

    if not logs_para_arquivar.exists():
        return True, "Nenhum log antigo para arquivar no momento."

    # 2. Serializar os dados para JSON
    logs_data = list(logs_para_arquivar.values(
        'id', 'ator_id', 'acao', 'alvo_content_type_id', 'alvo_id',
        'detalhes', 'data_criacao', 'hash_log'
    ))

    # Converte objetos datetime para string ISO 8601
    for log in logs_data:
        log['data_criacao'] = log['data_criacao'].isoformat()

    json_content = json.dumps(logs_data, indent=2, ensure_ascii=False)
    
    # 3. Preparar para o upload no S3
    timestamp = timezone.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_name = f"logs_archive_{timestamp}.json"
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_S3_REGION_NAME')
        )
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=json_content,
            ContentType='application/json'
        )
    except NoCredentialsError:
        return False, "Credenciais da AWS não encontradas. Verifique suas variáveis de ambiente."
    except ClientError as e:
        return False, f"Erro do cliente S3: {e}"
    except Exception as e:
        return False, f"Ocorreu um erro inesperado durante o upload para o S3: {e}"

    # 4. Marcar logs como arquivados
    ids_arquivados = [log['id'] for log in logs_data]
    LogAtividade.objects.filter(id__in=ids_arquivados).update(is_archived=True)

    return True, f"{len(ids_arquivados)} logs foram arquivados com sucesso em '{file_name}' no bucket '{bucket_name}'."




def criar_log(ator, acao, alvo=None, detalhes={}):
    """
    Cria uma nova entrada no Registro de Atividades de forma centralizada.
    """
    LogAtividade.objects.create(
        ator=ator,
        acao=acao,
        alvo=alvo,
        detalhes=detalhes
    )
    





def enviar_email_para_superusers(subject, message):
    """
    Busca todos os superusuários ativos e envia um e-mail de alerta para eles.
    """
    try:
        superusers = User.objects.filter(is_superuser=True, is_active=True)
        recipient_list = [su.email for su in superusers if su.email]
        
        if not recipient_list:
            print("ALERTA DE SEGURANÇA: NENHUM SUPERUSER COM EMAIL ENCONTRADO PARA NOTIFICAR.")
            return

        send_mail(
            subject=f"[ALERTA DE SEGURANÇA] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
    except Exception as e:
        # Em um projeto real, logue este erro em um serviço como Sentry
        print(f"FALHA AO ENVIAR E-MAIL DE ALERTA DE SEGURANÇA: {e}")
