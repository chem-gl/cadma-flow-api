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

try:  # Optional dependency (python-dotenv)
	from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
	load_dotenv = None  # type: ignore

BASE_ROOT = Path(__file__).resolve().parent.parent.parent
if load_dotenv:
	load_dotenv(BASE_ROOT / '.env', override=False)

if 'DJANGO_ENV' not in os.environ and 'PYTEST_CURRENT_TEST' in os.environ:
	os.environ['DJANGO_ENV'] = 'test'

env = os.getenv('DJANGO_ENV', 'local').lower()
module_map = {
	'local': 'cadmaflow.settings.local',
	'test': 'cadmaflow.settings.test',
	'ci': 'cadmaflow.settings.ci',
	'base': 'cadmaflow.settings.base',
}
selected = module_map.get(env, module_map['base'])
os.environ.setdefault('DJANGO_SETTINGS_MODULE', selected)
globals().update(import_module(selected).__dict__)
