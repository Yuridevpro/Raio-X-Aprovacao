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

if DEBUG:
    # Em desenvolvimento, permite explicitamente o servidor local.
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
else:
    # Em produção, exige que a variável de ambiente seja configurada.
    allowed_hosts_str = os.getenv('ALLOWED_HOSTS')
    if not allowed_hosts_str:
        ALLOWED_HOSTS = [] # Seguro: não permite ninguém se não estiver configurado
    else:
        ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',')]


# --- APLICAÇÕES INSTALADAS ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Nossos Apps
    'usuarios',
    'questoes',
    'pratica',
    'desempenho',
    # Apps de Terceiros
    'easymde',
    'storages', # Para integração com S3
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'usuarios.middleware.AdminSessionMiddleware',
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

# --- ARQUIVOS ESTÁTICOS E DE MÍDIA (DINÂMICO) ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'templates/static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

if DEBUG:
    # Em desenvolvimento, salvamos os arquivos localmente na pasta /media/
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
else:
    # Em produção, usamos o Amazon S3
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/'


# --- CONFIGURAÇÕES DE E-MAIL (DINÂMICO) ---
if DEBUG:
    # Em desenvolvimento, os e-mails são impressos no console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Em produção, usa um servidor SMTP real
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com' # Exemplo para Gmail
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')



# --- OUTRAS CONFIGURAÇÕES ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'

# NOMES DOS COOKIES DE SESSÃO ---
# Nome do cookie para o site do usuário final
SESSION_COOKIE_NAME = 'qconcurso_sessionid'
# Nome do cookie para o site de administração
ADMIN_SESSION_COOKIE_NAME = 'qconcurso_admin_sessionid'
# --- FIM DA ADIÇÃO ---