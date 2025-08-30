import os


def test_asgi_application_import():
    os.environ['DJANGO_ENV'] = 'test'
    import importlib
    asgi = importlib.import_module('cadmaflow.asgi')
    assert hasattr(asgi, 'application')


def test_wsgi_application_import():
    os.environ['DJANGO_ENV'] = 'test'
    import importlib
    wsgi = importlib.import_module('cadmaflow.wsgi')
    assert hasattr(wsgi, 'application')
