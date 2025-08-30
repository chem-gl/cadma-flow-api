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

## Documentación automática de calidad (SonarCloud)

El análisis de calidad y seguridad se ejecuta automáticamente en cada push y pull request a `main`/`master` mediante GitHub Actions (`.github/workflows/ci.yml`).

Resumen y métricas: https://sonarcloud.io/summary/new_code?id=cadma-flow

### Variables / Secrets requeridos en el repositorio

- `SONAR_TOKEN`: Token de proyecto/usuario con permiso de análisis.
- `SONAR_ORG`: Clave de la organización en SonarCloud.

### Ejecución manual local

```bash
export SONAR_TOKEN=xxxx
export SONAR_ORG=tu_org
pytest --cov=cadmaflow --cov-report=xml
pip install sonar-scanner-cli==5.0.1.3006
sonar-scanner -Dsonar.login=$SONAR_TOKEN -Dsonar.organization=$SONAR_ORG -Dproject.settings=sonar-project.properties
```

Los badges de este README se actualizan automáticamente tras cada análisis exitoso.

## Autoreload en desarrollo

Con Docker (usa volume + autoreload estándar de Django):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Puedes editar código y el servidor se recarga automáticamente. Para cambios en dependencias vuelve a reconstruir (`--build`).

## Health check

Ruta: `GET /health/` devuelve `{ "status": "ok" }`.

## Documentación de API (Swagger / OpenAPI)

Endpoints generados automáticamente con drf-spectacular:

- Esquema JSON: `GET /schema/` (OpenAPI 3)
- Swagger UI: `GET /docs/swagger/`
- Redoc: `GET /docs/redoc/`

Para agregar nuevas rutas documentadas, usa vistas DRF (APIView / ViewSets) y decoradores `@extend_schema`.
