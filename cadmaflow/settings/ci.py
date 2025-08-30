from .base import *

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "ci_db",
        "USER": "ci_user",
        "PASSWORD": "ci_pass",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
