# qconcurso/settings.py

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# --- CONFIGURAÇÕES DE AMBIENTE E SEGURANÇA ---
SECRET_KEY = os.getenv('SECRET_KEY')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production') # 'production' é o padrão seguro
DEBUG = (ENVIRONMENT == 'development')

# --- LÓGICA DE ALLOWED_HOSTS DEFINITIVA E ROBUSTA ---
if DEBUG:
    # Em desenvolvimento, permitimos o acesso local padrão.
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
else:
    # Em produção, começamos com uma lista vazia.
    ALLOWED_HOSTS = []
    
    # Adicionamos o hostname que o Render fornece automaticamente.
    # Esta é a forma mais segura de garantir que o seu site funcione no Render.
    render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
    if render_hostname:
        ALLOWED_HOSTS.append(render_hostname)
    
    # Adicionamos também qualquer domínio customizado que você configurar
    # na variável de ambiente ALLOWED_HOSTS.
    custom_hosts_str = os.getenv('ALLOWED_HOSTS')
    if custom_hosts_str:
        ALLOWED_HOSTS.extend([host.strip() for host in custom_hosts_str.split(',')])
# --- FIM DA CORREÇÃO ---


# --- APLICAÇÕES INSTALADAS ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',   # ✅ Adicione esta linha

    # Nossos Apps
    'usuarios.apps.UsuariosConfig',      # ALTERADO
    'questoes',
    'pratica',
    'desempenho',
    'ratelimit',
    'gestao',
    'simulados',
    'gamificacao.apps.GamificacaoConfig', # ALTERADO
    'storages', # Para integração com S3
    'django_bleach',
]

SITE_ID = 1


# =======================================================================
# ✅ INÍCIO DA ADIÇÃO: Configurações do Django Bleach
# =======================================================================
BLEACH_ALLOWED_TAGS = ['p', 'b', 'i', 'u', 'strong', 'em', 'strike', 'ul', 'ol', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br']

# Define quais atributos são permitidos em cada tag (nenhum neste caso, para segurança máxima)
BLEACH_ALLOWED_ATTRIBUTES = {}

# Remove completamente as tags que não estão na lista de permitidas.
BLEACH_STRIP_TAGS = True

# Não comenta o HTML inválido, apenas remove.
BLEACH_STRIP_COMMENTS = True
# =======================================================================
# FIM DA ADIÇÃO
# =======================================================================


# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'usuarios.middleware.ProfileMiddleware',
]

ROOT_URLCONF = 'qconcurso.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'usuarios.context_processors.avatar_equipado_processor',

            ],
        },
    },
]

WSGI_APPLICATION = 'qconcurso.wsgi.application'

# --- BANCO DE DADOS DINÂMICO ---
if DEBUG:
    # Em desenvolvimento, usamos o SQLite3, simples e rápido.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Em produção, usamos PostgreSQL, lendo as credenciais do .env
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# --- VALIDAÇÃO DE SENHA ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- INTERNACIONALIZAÇÃO ---
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# --- ARQUIVOS ESTÁTICOS (CONFIGURAÇÃO PARA PRODUÇÃO COM WHITENOISE) ---
# Esta parte permanece a mesma, pois Whitenoise lida com os arquivos estáticos
# do seu template (CSS, JS), não com os uploads dos usuários (mídia).
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'templates/static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- CONFIGURAÇÃO DE ARQUIVOS DE MÍDIA SEMPRE PARA O S3 ---
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')

# Configurações adicionais para garantir o funcionamento correto
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None # Recomendado para segurança
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_LOCATION = 'media' # Salva tudo dentro de uma pasta 'media' no bucket

# Define o storage padrão para os arquivos de mídia (uploads)
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# A URL base para acessar os arquivos de mídia no S3
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'



#  usa um servidor SMTP real
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com' # Exemplo para Gmail
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')



# --- OUTRAS CONFIGURAÇÕES ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'

