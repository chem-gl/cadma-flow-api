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
## Estructura (dominio actual)

```
cadmaflow/
   models/
      abstract_models.py        # AbstractMolecularData base genérica
      molecule.py               # Molecule, MolecularFamily
      workflow.py               # Workflow, WorkflowBranch
      execution.py              # WorkflowExecution
      step_execution.py         # StepExecution
      events.py                 # WorkflowEvent
      selection.py              # DataSelection (selección activa de variante)
      providers.py              # ProviderExecution (auditoría de runs)
      models.py                 # Shim de re-export temporal
   data_types/
      qsar.py                   # LogPData, ToxicityData, AbsorptionData, MutagenicityData
   providers/
      molecule_sets/
         base.py                 # MoleculeSetProviderBase (alias MoleculeSetProvider)
      properties_set/
         base.py                 # PropertyProviderBase (alias PropertySetProvider)
   workflows/
      steps/
         base.py                 # BaseStep abstracción
   utils/
      serializers.py
      validators.py
      branching.py
```

Notas:
- Carpetas legacy mal escritas (`molecules_set`, `propertie_set`) eliminadas.
- El shim `models/models.py` era temporal y los imports ya fueron migrados; puede eliminarse en una limpieza futura.
### Cómo crear un nuevo Provider

#### 1. Molecule Set Provider (`providers/molecule_sets/`)
Objetivo: generar una lista de descriptores de moléculas que se materializarán.

Pasos:
1. Crear archivo `providers/molecule_sets/my_source.py`.
2. Subclase de `MoleculeSetProviderBase`.
3. Definir `key`, `description`, opcional `params_spec`.
4. Implementar `fetch(self, *, params) -> Iterable[dict]` devolviendo dicts con al menos `inchikey`.
5. (Opcional) Validar parámetros sobrescribiendo `validate_params`.

Ejemplo mínimo:
```python
from cadmaflow.providers.molecule_sets.base import MoleculeSetProviderBase

class CsvMoleculeProvider(MoleculeSetProviderBase):
   key = "csv_molecules"
   description = "Carga moléculas desde un CSV con columnas inchikey, smiles, name"
   params_spec = {"path": {"type": "string", "required": True}}

   def fetch(self, *, params):
      path = params["path"]
      import csv
      with open(path) as fh:
         for row in csv.DictReader(fh):
            yield {"inchikey": row["inchikey"], "smiles": row.get("smiles"), "common_name": row.get("name")}
```

Consumirlo desde un Step (pseudo‑código):
```python
provider = CsvMoleculeProvider()
mol_dicts = provider.run(params={"path": "/tmp/mols.csv"})
# Luego cada dict se convierte a Molecule en la lógica del Step
```

#### 2. Property Provider (`providers/properties_set/`)
Objetivo: crear instancias de datos (`AbstractMolecularData`) para un conjunto de moléculas.

Pasos:
1. Archivo `providers/properties_set/my_props.py`.
2. Subclase de `PropertyProviderBase`.
3. Definir `key`, `description`, `produced_data_classes` (tuplas de clases de datos concretas).
4. Implementar `produce(self) -> list[AbstractMolecularData]`.
5. Dentro de `produce`, iterar moléculas y llamar `DataClass.retrieve_data(molecule=mol, method="user_input", config={...})` (u otro método).

Ejemplo mínimo:
```python
from cadmaflow.providers.properties_set.base import PropertyProviderBase
from cadmaflow.data_types.qsar import LogPData

class StaticLogPProvider(PropertyProviderBase):
   key = "static_logp"
   description = "Asigna un valor fijo de logP a todas las moléculas"
   produced_data_classes = (LogPData,)

   def produce(self):
      created = []
      for mol in self.molecules:
         created.append(LogPData.retrieve_data(molecule=mol, method="user_input", config={"value": 1.23}))
      return created
```

#### 3. Buenas prácticas
* Usa `key` estable y único (snake_case). Evita renombrarlo tras migraciones.
* Valida parámetros temprano; lanza `ValueError` con mensaje claro.
* Mantén producción de datos idempotente si se llama dos veces con la misma config (evitando duplicados innecesarios).
* Añade tests: creación básica, validación de parámetros, y que `produce` devuelve clases esperadas.
* Documenta el provider en este README si es reutilizable.

#### 4. Test rápido sugerido
```python
def test_static_logp_provider(db, molecule_factory):
   mol = molecule_factory()
   prov = StaticLogPProvider([mol])
   data = prov.produce()
   assert data and data[0].molecule == mol
```

## Producción (resumen)
* `DJANGO_ENV=base` o un settings específico
* `DEBUG=0`
**MoleculeSetProviderBase (abstracto)** (alias `MoleculeSetProvider`):
* Secret robusto
* Hosts configurados
* Servir estáticos con `collectstatic` detrás de un servidor (nginx + gunicorn/uvicorn)
**PropertyProviderBase (abstracto)** (alias `PropertySetProvider`):
| **models** | Molecule, MolecularFamily, AbstractMolecularData, Workflow, WorkflowBranch, WorkflowExecution, StepExecution, WorkflowEvent, DataSelection, ProviderExecution. |
| **data_types** | LogPData, ToxicityData, AbsorptionData, MutagenicityData (extensible). |
| **providers/molecule_sets** | MoleculeSetProviderBase (alias MoleculeSetProvider) + futuras implementaciones. |
| **providers/properties_set** | PropertyProviderBase (alias PropertySetProvider) + futuras implementaciones. |
| **Providers** | Subclases de MoleculeSetProviderBase. | Devuelven descriptores para crear Molecule/MolecularFamily. |
| **Providers de Propiedades** | Subclases de PropertyProviderBase. | Crean instancias de AbstractMolecularData. |
| Error conexión DB | Vars Postgres incompletas | Ver `.env` |
| Cobertura baja | Faltan tests | Añadir pruebas |
| 400 CSRF en dev | Request sin cookie | Usar sesión o desactivar según caso |

## Licencia
Revisar archivo `LICENSE`.

---
Contribuciones bienvenidas. Mantén los tests verdes antes de hacer PR.
## Estructura de Carpetas

```
cadma_flow/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── molecule.py
│   ├── abstract_models.py
│   └── enums.py
├── data_types/
│   ├── __init__.py
│   ├── base.py
│   ├── logp_data.py
│   ├── toxicity_data.py
│   └── ...
├── providers/
│   ├── __init__.py
│   ├── molecule_sets/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user_molecule_set.py
│   │   ├── test_molecule_set.py
│   │   └── ...
│   └── properties_set/
│       ├── __init__.py
│       ├── base.py
│       ├── logp_provider.py
│       ├── toxicity_provider.py
│       └── ...
├── workflows/
│   ├── __init__.py
│   ├── base.py
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── data_acquisition_step.py
│   │   ├── calculation_step.py
│   │   └── ...
│   └── executions/
│       ├── __init__.py
│       ├── workflow_execution.py
│       ├── step_execution.py
│       └── ...
└── utils/
    ├── __init__.py
    ├── serializers.py
    └── validators.py
```

