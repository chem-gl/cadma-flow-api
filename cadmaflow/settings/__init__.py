"""Dynamic settings loader with .env support.

Priority for DJANGO_ENV:
1. Explicit environment variable
2. If running under pytest (PYTEST_CURRENT_TEST present) -> 'test'
3. Fallback 'local'

Loads variables from a .env file at project root if present.
"""
import os
from importlib import import_module
from pathlib import Path
from typing import Callable

# Explicit Optional annotation so assigning None passes mypy
load_dotenv: Callable[..., bool] | None
try:  # Optional dependency (python-dotenv)
	from dotenv import load_dotenv as _real_load_dotenv  # type: ignore
	load_dotenv = _real_load_dotenv
except Exception:  # pragma: no cover
	load_dotenv = None

BASE_ROOT = Path(__file__).resolve().parent.parent.parent

# Record whether DJANGO_ENV was explicitly present (shell/export) before reading .env
_had_explicit_django_env = 'DJANGO_ENV' in os.environ

if load_dotenv is not None:  # Load .env only if dependency available
	load_dotenv(BASE_ROOT / '.env', override=False)

# If running under pytest and the user did NOT explicitly export DJANGO_ENV
# we force the test settings even if .env provides a value.
# If running under pytest and DJANGO_ENV wasn't explicitly exported we force 'test'.
# If it WAS explicitly exported we respect the user's intention (e.g. forcing 'ci').
if 'PYTEST_CURRENT_TEST' in os.environ and not _had_explicit_django_env:
	os.environ['DJANGO_ENV'] = 'test'

raw_env = os.getenv('DJANGO_ENV', 'local')
env = raw_env.lower()
module_map = {
	'local': 'cadmaflow.settings.local',
	'test': 'cadmaflow.settings.test',
	'ci': 'cadmaflow.settings.ci',
	'base': 'cadmaflow.settings.base',
}
unknown_env = env not in module_map
selected = module_map.get(env, module_map['base'])
os.environ.setdefault('DJANGO_SETTINGS_MODULE', selected)
settings_mod = import_module(selected)

# If we fell back due to unknown environment name, enforce a deterministic
# sqlite configuration regardless of external DATABASE_* env vars so tests
# (and local tooling) behave predictably.
if unknown_env:
	default_db = getattr(settings_mod, 'DATABASES', {}).get('default', {})
	default_db['ENGINE'] = 'django.db.backends.sqlite3'
	default_db['NAME'] = getattr(settings_mod, 'BASE_DIR', BASE_ROOT) / 'db.sqlite3'
	settings_mod.DATABASES = {'default': default_db}  # type: ignore

globals().update(settings_mod.__dict__)
