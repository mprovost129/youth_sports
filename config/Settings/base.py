from pathlib import Path
import os
import re
from urllib.parse import parse_qs, urlparse, unquote

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.signals import connection_created
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# config/Settings/base.py -> .parent = Settings, .parent = config, .parent = project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from project root
load_dotenv(BASE_DIR / '.env')


def _postgres_config_from_database_url(database_url: str) -> dict:
    parsed = urlparse(database_url)

    if parsed.scheme not in ('postgres', 'postgresql'):
        raise ImproperlyConfigured('DATABASE_URL must use postgres/postgresql scheme.')

    db_name = parsed.path.lstrip('/')
    if not db_name:
        raise ImproperlyConfigured('DATABASE_URL must include a database name in the path.')

    query = parse_qs(parsed.query)

    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(db_name),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname or 'localhost',
        'PORT': str(parsed.port or 5432),
        # Render commonly requires SSL for managed Postgres connections.
        'OPTIONS': {
            'sslmode': query.get('sslmode', ['require'])[0],
        },
    }

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'axes',
    # Local
    'users',
    'core',
]

AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Axes — brute-force login protection
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_CALLABLE = None  # uses default 403 response

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
SERVE_MEDIA = os.environ.get('SERVE_MEDIA', '').strip().lower() in ('1', 'true', 'yes', 'on')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Cache — overridden per environment
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Database
database_url = os.environ.get('DATABASE_URL')
if database_url:
    default_db = _postgres_config_from_database_url(database_url)
else:
    default_db = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }

DB_SCHEMA = os.environ.get('DB_SCHEMA', 'youth_sports')
if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', DB_SCHEMA):
    raise ImproperlyConfigured(
        'DB_SCHEMA must be a valid PostgreSQL schema identifier (letters, numbers, underscores).'
    )

# Pin connections to this schema so Django never falls back to shared public tables.
db_options = default_db.setdefault('OPTIONS', {})
search_path_option = f'-c search_path={DB_SCHEMA}'
existing_options = db_options.get('options', '').strip()
if existing_options:
    db_options['options'] = f'{existing_options} {search_path_option}'
else:
    db_options['options'] = search_path_option

DATABASES = {
    'default': default_db,
}


def _set_connection_schema(sender, connection, **kwargs):
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        cursor.execute(f'SET search_path TO "{DB_SCHEMA}"')


connection_created.connect(_set_connection_schema)

# Email
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'webmaster@localhost')
