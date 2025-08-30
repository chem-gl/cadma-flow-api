import importlib
import sys


def _purge_settings_modules():
    # Snapshot keys to avoid RuntimeError dict changed size during iteration
    for m in tuple(sys.modules.keys()):  # snapshot keys safely
        if m.startswith('cadmaflow.settings'):
            sys.modules.pop(m, None)


def test_import_local_settings(monkeypatch):
    monkeypatch.setenv('DJANGO_ENV', 'local')
    _purge_settings_modules()
    # Import concrete local module for coverage
    local_mod = importlib.import_module('cadmaflow.settings.local')
    assert local_mod.DEBUG is True
    settings_pkg = importlib.import_module('cadmaflow.settings')
    assert settings_pkg.DEBUG is True


def test_import_ci_settings(monkeypatch):
    monkeypatch.setenv('DJANGO_ENV', 'ci')
    _purge_settings_modules()
    ci_mod = importlib.import_module('cadmaflow.settings.ci')
    default_db = ci_mod.DATABASES['default']
    assert default_db['ENGINE'].endswith('postgresql')
    settings_pkg = importlib.import_module('cadmaflow.settings')
    assert settings_pkg.DATABASES['default']['ENGINE'].endswith('postgresql')


def test_unknown_env_falls_back_to_base(monkeypatch):
    monkeypatch.setenv('DJANGO_ENV', 'does_not_exist')
    _purge_settings_modules()
    settings_pkg = importlib.import_module('cadmaflow.settings')
    # base uses sqlite3
    assert settings_pkg.DATABASES['default']['ENGINE'].endswith('sqlite3')


def test_pytest_auto_sets_test_env(monkeypatch):
    # Simulate absence of explicit DJANGO_ENV but presence of PYTEST_CURRENT_TEST
    monkeypatch.delenv('DJANGO_ENV', raising=False)
    monkeypatch.setenv('PYTEST_CURRENT_TEST', 'dummy::test')
    _purge_settings_modules()
    settings_pkg = importlib.import_module('cadmaflow.settings')
    # test settings switch DEBUG False and in-memory sqlite
    assert settings_pkg.DEBUG is False
    assert settings_pkg.DATABASES['default']['NAME'] == ':memory:'


def test_allowed_hosts_parsing(monkeypatch):
    monkeypatch.setenv('DJANGO_ENV', 'local')
    monkeypatch.setenv('DJANGO_ALLOWED_HOSTS', 'a.com,b.com')
    _purge_settings_modules()
    settings_pkg = importlib.import_module('cadmaflow.settings')
    assert settings_pkg.ALLOWED_HOSTS == ['a.com', 'b.com']


def test_secret_key_override(monkeypatch):
    monkeypatch.setenv('DJANGO_ENV', 'local')
    monkeypatch.setenv('DJANGO_SECRET_KEY', 'xxx-secret')
    _purge_settings_modules()
    settings_pkg = importlib.import_module('cadmaflow.settings')
    assert settings_pkg.SECRET_KEY == 'xxx-secret'


def test_debug_false_via_env(monkeypatch):
    monkeypatch.setenv('DJANGO_ENV', 'local')
    monkeypatch.setenv('DJANGO_DEBUG', '0')
    _purge_settings_modules()
    settings_pkg = importlib.import_module('cadmaflow.settings')
    assert settings_pkg.DEBUG is False
