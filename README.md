# CADMA Flow

Proyecto Django configurado con:

- Django 5
- Pytest + cobertura (coverage.xml)
- Integración SonarCloud
- Workflow GitHub Actions (tests + análisis Sonar + Quality Gate)
- Carga dinámica de settings por `DJANGO_ENV` (local, test, ci, base)

## Variables de entorno clave

- `DJANGO_ENV` (local|test|ci|base)
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS` (lista separada por comas)

En CI se usan secrets: `SONAR_TOKEN` y `SONAR_ORG`.

Archivo `.env` (crear desde `.env.example`):
```
DJANGO_ENV=local
DJANGO_SECRET_KEY=clave-super-secreta
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

Cuando ejecutas pytest no necesitas exportar `DJANGO_ENV`; si no está fijado se fuerza `test` automáticamente.

## Ejecutar local

### Con pyenv + pip
```bash
pyenv install 3.12.4 # si no lo tienes
pyenv virtualenv 3.12.4 cadma-flow || true
pyenv local cadma-flow
pip install -U pip
pip install -r requirements.txt
export DJANGO_ENV=local
python manage.py migrate
python manage.py runserver
```

## Ejecutar tests

```bash
pytest
```

## Health check

Ruta: `GET /health/` devuelve `{ "status": "ok" }`.
