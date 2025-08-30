"""Base Django settings for cadmaflow project.

Environment selection is handled in ``cadmaflow.settings.__init__`` using
the DJANGO_ENV variable (base|local|test|ci). These base settings are
extended/overridden by the environment specific modules.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

SQLITE_ENGINE = 'django.db.backends.sqlite3'

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY: secret key & debug via env vars (with safe defaults for dev/tests)
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-placeholder-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes', 'on')
ALLOWED_HOSTS = [h for h in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if h] or []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Project apps
    'cadmaflow.core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cadmaflow.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'cadmaflow.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

_db_url = os.getenv('DATABASE_URL')
if _db_url:
    parsed = urlparse(_db_url)
    if parsed.scheme.startswith('postgres'):
        DB_ENGINE = 'django.db.backends.postgresql'
    elif parsed.scheme in ('mysql', 'mariadb'):
        DB_ENGINE = 'django.db.backends.mysql'
    elif parsed.scheme in ('sqlite', 'file'):
        DB_ENGINE = SQLITE_ENGINE
    else:
        DB_ENGINE = SQLITE_ENGINE

    if DB_ENGINE == SQLITE_ENGINE:
        DB_NAME = parsed.path.lstrip('/') or (BASE_DIR / 'db.sqlite3')
    else:
        DB_NAME = parsed.path.lstrip('/')

    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': DB_NAME,
            'USER': parsed.username or '',
            'PASSWORD': parsed.password or '',
            'HOST': parsed.hostname or '',
            'PORT': parsed.port or '',
        }
    }
elif os.getenv('POSTGRES_DB'):
    # Build from discrete POSTGRES_* env vars (preferred for docker-compose)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB'),
            'USER': os.getenv('POSTGRES_USER', ''),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
else:
    # Final fallback (development only)
    DATABASES = {
        'default': {
            'ENGINE': SQLITE_ENGINE,
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
