# CADMA Flow
Servicio Django / DRF listo para desarrollo rápido y CI básico.

## Stack principal
* Python 3.12
* Django 5
* Django REST Framework
* drf-spectacular (OpenAPI / Swagger / Redoc)
* Pytest + coverage
* Carga dinámica de settings vía `DJANGO_ENV` (`local`, `test`, `ci`, `base`)
* GitHub Actions (tests + verificación de endpoint health)

## Settings dinámicos
El módulo `cadmaflow/settings/__init__.py` selecciona el archivo según `DJANGO_ENV` con la siguiente prioridad:
1. Variable de entorno `DJANGO_ENV`
2. Si se ejecuta pytest y no está definida, fuerza `test`
3. Fallback `local`

## Variables de entorno clave
Obligatorias / recomendadas:
* `DJANGO_ENV` (local|test|ci|base)
* `DJANGO_SECRET_KEY`
* `DJANGO_ALLOWED_HOSTS` (lista separada por comas)
* `DJANGO_DEBUG` (1/0)

Base de datos (PostgreSQL opcional):
* `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
	o `DATABASE_URL` (`postgres://user:pass@host:5432/db`)

Ejemplo `.env` (copiar desde `.env.example`):
```bash
DJANGO_ENV=local
DJANGO_SECRET_KEY=clave-super-secreta
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=cadma
POSTGRES_USER=cadma
POSTGRES_PASSWORD=cadma
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Al correr `pytest` no hace falta exportar `DJANGO_ENV`; si no existe se usa `test` automáticamente.

## Instalación local (pyenv + pip)
```bash
pyenv install 3.12.4 || true
pyenv virtualenv 3.12.4 cadma-flow || true
pyenv local cadma-flow
pip install -U pip
pip install -r requirements.txt
cp .env.example .env  # Ajusta valores
python manage.py migrate
python manage.py runserver
```

## Docker (desarrollo con autoreload)
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```
Edita código y Django recarga. Si cambias dependencias reconstruye la imagen.

## Migraciones y superusuario
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```
Admin: http://localhost:8000/admin/

## Tests y cobertura
```bash
pytest
pytest --cov=cadmaflow --cov-report=term-missing --cov-report=xml
```
`coverage.xml` se genera para integraciones externas si hicieran falta.

## Endpoint Health
`GET /health/` -> `{ "status": "ok" }` (usado en CI para comprobar arranque).

## Documentación de API
* Esquema: `GET /schema/`
* Swagger UI: `GET /docs/swagger/`
* Redoc: `GET /docs/redoc/`

Ejemplo de documentación con decorador:
```python
from drf_spectacular.utils import extend_schema

@extend_schema(summary="Ping", description="Devuelve pong")
class PingView(APIView):
		...
```

## Crear nueva app
```bash
python manage.py startapp nombre_app
```
Añade la app a `INSTALLED_APPS`.

## Producción (resumen)
* `DJANGO_ENV=base` o un settings específico
* `DEBUG=0`
* Secret robusto
* Hosts configurados
* Servir estáticos con `collectstatic` detrás de un servidor (nginx + gunicorn/uvicorn)
* TLS, logs y backups de DB

## Tabla rápida de problemas
| Problema | Posible causa | Acción |
|----------|---------------|--------|
| 404 /docs/swagger/ | Falta drf-spectacular | Revisar `INSTALLED_APPS` |
| Error conexión DB | Vars Postgres incompletas | Ver `.env` |
| Cobertura baja | Faltan tests | Añadir pruebas |
| 400 CSRF en dev | Request sin cookie | Usar sesión o desactivar según caso |

## Licencia
Revisar archivo `LICENSE`.

---
Contribuciones bienvenidas. Mantén los tests verdes antes de hacer PR.
