import os
import sys

import pytest


@pytest.mark.django_db
def test_settings_unknown_env_fallback(monkeypatch):
    monkeypatch.setenv('DJANGO_ENV', 'weird_env_x')
    sys.modules.pop('cadmaflow.settings', None)
    from django.conf import settings as dj_settings

    import cadmaflow.settings  # noqa: F401
    assert os.environ.get('DJANGO_ENV') == 'weird_env_x'
    assert dj_settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'


@pytest.mark.django_db
def test_settings_explicit_env_not_overridden(monkeypatch):
    monkeypatch.setenv('DJANGO_ENV', 'ci')
    sys.modules.pop('cadmaflow.settings', None)
    import cadmaflow.settings  # noqa: F401
    assert os.environ.get('DJANGO_ENV') == 'ci'