from .base import *  # noqa
import os

# Local development overrides (env can override)
_prev_debug = globals().get('DEBUG', True)
DEBUG = os.getenv('DJANGO_DEBUG', str(_prev_debug)).lower() in ('1', 'true', 'yes', 'on')
_env_hosts = os.getenv('DJANGO_ALLOWED_HOSTS')
if _env_hosts:
	ALLOWED_HOSTS = [h.strip() for h in _env_hosts.split(',') if h.strip()]  # type: ignore # noqa: F821
else:
	ALLOWED_HOSTS = ["localhost", "127.0.0.1"]  # type: ignore # noqa: F821

_base_dir = globals().get('BASE_DIR')
DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': _base_dir / 'db.sqlite3' if _base_dir else 'db.sqlite3',
	}
}
