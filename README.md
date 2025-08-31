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

## Clases y sus Responsabilidades

### 1. Modelos Base (models/)

**Molecule**: Ya está implementado, representa una molécula única con identificadores y propiedades básicas.

**AbstractMolecularData**: Clase abstracta base para todos los datos moleculares:
- Define la estructura común para almacenar datos moleculares
- Implementa sistema de tipos fuertes con TypeVar
- Gestiona serialización/deserialización automática
- Controla metadatos de procedencia y calidad de datos
- Implementa el patrón de congelación de datos

### 2. Tipos de Datos (data_types/)

**LogPData, ToxicityData, etc.**: Clases concretas que heredan de AbstractMolecularData:
- Definen tipos específicos de datos moleculares
- Implementan métodos abstractos para serialización/deserialización
- Especifican métodos de obtención disponibles para ese tipo de dato
- Definen validaciones específicas para el tipo de dato

### 3. Providers de Conjuntos Moleculares (providers/molecule_sets/)

**ProviderMoleculeSet (abstracto)**:
- Genera conjuntos de moléculas a partir de diferentes fuentes
- Puede recibir parámetros de configuración
- Implementa métodos para obtener moléculas de diversas fuentes (USER, TEST, AMBIT, etc.)

**Implementaciones concretas**:
- UserMoleculeSet: moléculas proporcionadas por usuarios
- TestMoleculeSet: moléculas de la base de datos T.E.S.T.
- AmbitMoleculeSet: moléculas de AMBIT
- ...

### 4. Providers de Propiedades (providers/properties_set/)

**ProviderPropertiesSet (abstracto)**:
- Recibe un conjunto de moléculas como entrada
- Calcula propiedades para todas las moléculas del conjunto
- Define qué tipos de datos puede generar (Lista de clases AbstractMolecularData)
- Puede utilizar diferentes métodos/algoritmos para el cálculo

**Implementaciones concretas**:
- LogPProvider: calcula logP para un conjunto de moléculas
- ToxicityProvider: calcula toxicidad para un conjunto de moléculas
- DrugbilityProvider: calcula propiedades de drugabilidad
- ...

### 5. Steps del Workflow (workflows/steps/)

**BaseStep (abstracto)**:
- Define la interfaz común para todos los pasos del workflow
- Especifica requisitos de entrada (conjuntos moleculares y tipos de datos)
- Define resultados esperados (conjuntos moleculares y tipos de datos producidos)
- Implementa lógica de ejecución y seguimiento del progreso
- Gestiona la configuración y parámetros del paso

**Implementaciones concretas**:
- DataAcquisitionStep: obtiene datos de providers externos
- CalculationStep: ejecuta cálculos sobre los datos
- FilterStep: filtra moléculas basado en criterios
- AnalysisStep: realiza análisis sobre los resultados

### 6. Workflows (workflows/)

**FLUJO (Workflow)**:
- Define una secuencia de pasos a ejecutar
- Gestiona la ejecución del flujo completo
- Mantiene el estado y progreso del workflow
- Permite la creación de ramas cuando se cambian parámetros

**WorkflowExecution**:
- Representa una ejecución concreta de un workflow
- Almacena el estado, resultados y metadatos de la ejecución
- Gestiona el avance a través de los pasos del workflow

**StepExecution**:
- Representa la ejecución de un paso específico
- Almacena snapshot de datos de entrada y resultados
- Mantiene el estado de ejecución del paso

### 7. Ejecuciones (workflows/executions/)

Estas clases gestionan el estado de las ejecuciones:
- WorkflowExecution: estado completo de una ejecución de workflow
- StepExecution: estado de la ejecución de un paso individual
- Gestionan la persistencia de datos de entrada y resultados

## Flujo de Trabajo Típico

1. Se crea un Workflow con una secuencia de Steps definida
2. Para cada ejecución:
   - Se crea una WorkflowExecution
   - Para cada Step en el workflow:
     - Se crea una StepExecution con snapshot de datos de entrada
     - Se ejecuta el Step con sus parámetros
     - Se guardan los resultados en la StepExecution
   - Los resultados de un Step alimentan al siguiente Step
3. Si se modifican parámetros en un Step que permite branching, se crea una nueva rama de ejecución

## Ventajas de esta Estructura

1. **Separación de responsabilidades**: Cada componente tiene una función clara
2. **Extensibilidad**: Fácil agregar nuevos tipos de datos, providers o steps
3. **Reproducibilidad**: Los snapshots garantizan que las ejecuciones sean reproducibles
4. **Flexibilidad**: Los workflows pueden recombinarse fácilmente
5. **Tracking**: Todo el proceso queda registrado para auditoría y análisis


# Manual de Diseño – Cadma Flow  
## Patrón de Workflows con Ramas y Congelación de Datos  

A continuación tienes la especificación completa (sin código) de **qué debe hacer cada clase**, cómo se relacionan entre sí y cuál es el flujo de control que permite:

* 1⃣ Crear un **workflow** (una serie de pasos).  
* 2⃣ Ejecutar el workflow creando **snapshots** de los datos que entran y salen de cada paso.  
* 3⃣ Congelar (“freeze”) los datos para que no puedan cambiarse accidentalmente.  
* 4⃣ Si se desea modificar un dato congelado, el sistema genera automáticamente una **rama** (branch) que hereda los datos congelados del punto de origen y permite la nueva variante sin destruir la historia.  

El modelo está basado en los patrones de **Command**, **Memento**, **State**, **Builder** y **Composite** – los cuales ya están probados en sistemas de pipelines científicos y de ETL.  

---

## 1⃣  Ámbito de cada paquete

| Paquete | Propósito | Comentario clave |
|---------|-----------|-------------------|
| **models** | Definición de los *modelos de dominio* (Molecule, AbstractMolecularData, enums). | Son objetos “persistentes” (Django ORM). |
| **data_types** | Sub‑clases concretas de `AbstractMolecularData` (LogPData, ToxicityData, …). | Cada tipo conoce cómo (des)serializarse y qué métodos de obtención existen. |
| **providers** | Conectores externos que entregan **conjuntos** de moléculas o de propiedades. | Se subdividen en `molecule_sets` y `properties_set`. |
| **workflows** | Motor de ejecución del pipeline: definición del flujo, ejecución, historial y ramas. | Contiene la lógica de “branching” y “freezing”. |
| **utils** | Funciones auxiliares (serializadores, validadores, helpers de branching). | No forman parte del dominio, solo facilitan la implementación. |

---

## 2⃣  Modelos Base (`models/`)

### 2.1 `Molecule`
- **Responsabilidad**: Entidad única que representa una molécula.  
- **Campos clave**: `smiles`, `inchi`, `inchikey`, `molecular_formula`, `molecular_weight`, `common_name`, `is_reference`.  
- **Métodos de utilidad**:  
  - `get_data(AbstractMolecularData, source?, user_tag?)` – devuelve QuerySet de datos asociados.  
  - `get_or_create_data(AbstractMolecularData, method, config?, user_tag?)` – busca un dato ya creado o delega a `retrieve_data`.  
  - `ensure_all([(DataClass, method), …], config_map?)` – garantiza que todos los datos requeridos existan (crea si falta).  

### 2.2 `AbstractMolecularData`
- **Tipo**: Modelo **abstracto** que actúa como *Memento* de un valor químico.  
- **Responsabilidades**:  
  1. **Almacenar** el valor (como JSON) y su **tipo nativo** (`native_type`).  
  2. **Versionar** el dato mediante los campos de congelación (`is_frozen`, `frozen_at`, `frozen_by`).  
  3. **Rastrear la procedencia** (`source`, `source_name`, `source_version`, `provider_execution`).  
  4. **Validar** que el valor sea del tipo esperado (métodos `get_native_type`, `get_value_type`, `validate_value_type`).  
  5. **Exponer** la API de (de)serialización (`serialize_value`, `deserialize_value`).  
  6. **Definir** los métodos de obtención disponibles (`get_data_retrieval_methods`) y la lógica de recuperación (`retrieve_data`).  
- **Patrón**: **Memento** (snapshot de un valor) + **Strategy** (diferentes métodos de obtención).  

### 2.3 Enums (`enums.py`)
- `SourceChoices`, `NativeTypeChoices`, `StatusChoices`.  
- **Uso**: Evitan “magic strings” y garantizan consistencia en la base de datos y en el código.

---

## 3⃣  Tipos de Datos (`data_types/`)

Cada sub‑clase (p. ej. `LogPData`, `ToxicityData`) **hereda** de `AbstractMolecularData` y **cumple** con:

| Obligación | Qué implica |
|------------|--------------|
| `get_native_type()` | Devuelve una de las opciones de `NativeTypeChoices` (FLOAT, LIST, …). |
| `get_value_type()` | Devuelve el tipo Python real (`float`, `list[dict]`, …). |
| `serialize_value(value)` | Convierte el valor a *string JSON* (usando `json.dumps` o `orjson`). |
| `deserialize_value(serialized)` | Convierte el JSON a la estructura Python correspondiente. |
| `get_data_retrieval_methods()` | Diccionario que describe los **métodos** disponibles (p. ej. `"rdkit_logp": {"description": "...", "config_schema": {...}}`). |
| `retrieve_data(molecule, method, config, user_tag)` | Implementa la lógica para crear la instancia del dato usando el método indicado (p. ej. llama a RDKit, a un servicio REST, etc.). |

> **Tip**: Mantén `data_retrieval_methods` **declarativo** (JSON‑schema) para que el motor del workflow pueda ofrecer al usuario un “formulario dinámico” de parámetros.

---

## 4⃣  Providers (`providers/`)

### 4.1 `ProviderMoleculeSet` (abstracto)

| Responsabilidad | Detalle |
|-----------------|----------|
| **Crear** un conjunto de moléculas a partir de una fuente externa. | Ej.: leer un CSV, consultar la API de AMBIT, generar una cuadrícula de estructuras. |
| **Recibir** parámetros de configuración (p. ej. `source=SourceChoices.USER`, `max_molecules=500`). | La firma típica es `def get_molecule_set(self, **config) -> MoleculeSet:`. |
| **Exponer** metadatos de la generación (quién lo creó, cuándo, versión del provider). | Necesario para rastrear la procedencia y para la congelación. |

#### Implementaciones típicas
- `UserMoleculeSet`: toma un fichero subido por el usuario.  
- `TestMoleculeSet`: devuelve la lista de moléculas pre‑definidas de la base T.E.S.T.  
- `AmbitMoleculeSet`: consulta la API de AMBIT con un filtro de actividad.  

### 4.2 `ProviderPropertiesSet` (abstracto)

| Responsabilidad | Detalle |
|-----------------|----------|
| **Recibir** un `MoleculeSet` (lista de `Molecule`). | La lista proviene de cualquier `ProviderMoleculeSet` o de un paso anterior. |
| **Calcular** uno o varios tipos de datos (`AbstractMolecularData`) para *todas* las moléculas del set. | Cada provider declara la lista de clases de datos que puede producir. |
| **Configurar** el cálculo mediante un esquema de parámetros (p. ej. número de procesos, versión del algoritmo). | Permite que el workflow muestre al usuario un formulario con validación automática. |
| **Registrar** una `ProviderExecution` que almacena la información del *run* (tiempo, versión, parámetros). | Facilita la trazabilidad y la congelación posterior. |

#### Implementaciones típicas
- `LogPProvider`: calcula logP con RDKit o con un modelo ML.  
- `ToxicityProvider`: consulta el API de ProTox‑II.  
- `GaussianProvider`: lanza cálculos de QM vía Gaussian y devuelve energías, dipolos, etc.  

---

## 5⃣  Motor del Workflow (`workflows/`)

### 5.1 `BaseStep` (abstracto)

| Categoría | Responsabilidad |
|-----------|-----------------|
| **Metadatos** | `name`, `description`, `order`, `allows_branching`, `parameters_schema`. |
| **Dependencias** | `required_molecule_set` (clase de `MoleculeSetAbstract`), `produced_molecule_set`; `required_data_classes` (lista de clases de `AbstractMolecularData`), `produced_data_classes`. |
| **Ejecución** | `execute(step_execution, parameters)` – orquesta: <br>1⃣ Carga el snapshot de entrada (`step_execution.input_snapshot`). <br>2⃣ Valida que todas las dependencias estén satisfechas (`can_execute`). <br>3⃣ Llama a `_process_step` (implementado por la sub‑clase). <br>4⃣ Guarda los resultados (`step_execution.results`, `status`). |
| **Hooks** | `_process_step` – lógica concreta del step; `can_execute` – verifica pre‑condiciones; `get_progress` – cálculo del % de datos ya preparados. |
| **Branching** | Si `allows_branching=True` y el usuario cambia algún parámetro o dato de entrada, el motor debe crear una nueva rama (ver sección **6**). |

> **Patrón**: **Command** (cada Step es un comando que puede ejecutarse, deshacerse, volver a ejecutarse).  

### 5.2 `Workflow` (antes “FLUJO”)

| Campo | Significado |
|-------|--------------|
| `id` | PK del workflow (UUID). |
| `name` | Nombre legible. |
| `description` | Texto libre. |
| `steps` | Lista ordenada de objetos `BaseStep`. |
| `initial_step` | Referencia al primer `BaseStep`. |
| `created_at/updated_at` | Auditar. |
| `status` | `StatusChoices` (PENDING, RUNNING, …). |
| `branch_of` | FK a otro `Workflow` si es una **rama** (null si es la rama principal). |
| `root_branch` | FK al workflow raíz (auto‑referencia). |
| `frozen_at` / `frozen_by` | Cuando el workflow entero queda congelado (opcional). |

**Responsabilidades**:

1. **Orquestar** la ejecución de los pasos en el orden definido.  
2. **Mantener** el estado global del workflow (`status`).  
3. **Crear** objetos `WorkflowExecution` y `StepExecution` (ver sección 6).  
4. **Gestionar** ramas: si un usuario modifica parámetros o datos de un paso que permite branching, se crea una **nueva instancia** de `Workflow` con `branch_of = workflow_actual`. La nueva rama hereda:
   - Los *snapshots* de datos congelados de los pasos anteriores.  
   - Los *providers* y *configuraciones* de los pasos que no se modificaron.  
   - Un **identificador** de la rama (`branch_label` o `branch_number`).  

### 5.3 `WorkflowExecution`

| Campo | Descripción |
|-------|--------------|
| `workflow` | FK al `Workflow` que se está ejecutando. |
| `started_at`, `finished_at` | Timestamps. |
| `status` | `StatusChoices`. |
| `current_step_index` | Índice del paso que está en ejecución o que será ejecutado a continuación. |
| `branch_label` | Texto opcional para distinguir la rama (p. ej. “v2‑high‑temp”). |
| `parent_execution` | FK a la ejecución de la rama origen (null si es la ejecución raíz). |
| `snapshots` | Relación a `StepExecution` (uno‑a‑muchos). |

**Responsabilidades**:

- Representar una *instancia* del workflow (cada vez que el usuario pulsa “Run”).  
- Guardar el **histórico** de los snapshots de cada paso (`StepExecution`).  
- Proveer métodos de *rewind* (volver a un snapshot anterior) y *re‑run* (ejecutar de nuevo a partir de un paso).  

### 5.4 `StepExecution`

| Campo | Significado |
|-------|--------------|
| `workflow_execution` | FK a la ejecución a la que pertenece. |
| `step` | FK al `BaseStep` que se está ejecutando. |
| `input_snapshot` | JSON que contiene **todos** los datos de entrada congelados (moleculas, valores, configuraciones). |
| `results` | JSON con los resultados producidos (IDs de `AbstractMolecularData`, métricas, etc.). |
| `status` | `StatusChoices` (PENDING, RUNNING, COMPLETED, FAILED). |
| `started_at`, `completed_at` | Timestamps. |
| `branch_of` | Si el step se ejecutó en una rama, referencia a la ejecución original (permite “track back”). |

**Responsabilidades**:

- Actuar como **Memento** de la ejecución de un paso.  
- Guardar **snapshot** de entrada antes de que el paso modifique cualquier dato.  
- Al terminar, almacenar los **resultados** y marcar el paso como completado.  

> **Nota importante**: Todos los campos que pueden cambiar (p. ej. valores de `AbstractMolecularData`) **se congelan** antes de la ejecución del paso y se guardan en `input_snapshot`. De esa manera, aunque los datos cambien en la base de datos después, el snapshot sigue siendo idéntico al momento de la ejecución.

---

## 6⃣  Branching & Congelación (el “core” del requerimiento)

### 6.1 Congelación de datos (`AbstractMolecularData.freeze(user)`)

- Cambia `is_frozen=True`, registra `frozen_at` y `frozen_by`.  
- Después, **cualquier intento de `set_value`** lanza `RuntimeError`.  
- Los **snapshots** de los pasos ya ejecutados guardan el **valor congelado**; si el dato se congela *después* de un paso, el snapshot ya contiene el valor original y no se verá afectado.

### 6.2 Creación de una rama

1. **Detección**: Cuando el usuario modifica:
   - Un **parámetro** del step (`parameters_schema`) **o**  
   - Un **dato** de entrada que está congelado (p. ej. quiere usar una versión distinta de `LogPData`).  

2. **Regla**:  
   - Si el step tiene `allows_branching=False` → **Error** (no se permite la rama).  
   - Si `allows_branching=True` → el motor crea una **nueva instancia** de `Workflow` (o de `WorkflowExecution` dependiendo del nivel de granularidad que prefieras).  

3. **Datos heredados**:  
   - El nuevo workflow copia **todos los snapshots** de los pasos anteriores (es decir, los datos congelados).  
   - Los `ProviderExecution` de los pasos ya ejecutados se reutilizan (no se vuelven a lanzar).  

4. **Nuevo snapshot**:  
   - Para el paso que cambió, se crea un nuevo `StepExecution` con un `input_snapshot` que incluye los **nuevos** valores o parámetros.  

5. **Persistencia de la rama**:  
   - En la tabla `Workflow` se guarda `branch_of` → workflow del que proviene.  
   - En la tabla `WorkflowExecution` se guarda `parent_execution` → ejecución de la rama origen.  
   - Se genera automáticamente un **identificador legible** (`branch_label`) como `main‑v2‑logP‑highTemp` o `#3` (incremental).  

### 6.3 Visualización del árbol de ramas

| Clase | Campo clave |
|-------|-------------|
| `Workflow` | `branch_of` (FK a Workflow). |
| `WorkflowExecution` | `parent_execution` (FK a WorkflowExecution). |

Con estos dos campos puedes construir un árbol de versiones (similar a Git): cada nodo tiene un único padre, pero puede tener **cualesquiera** hijos (ramas).  

**Operaciones habituales**:

| Operación | Qué hace | Qué tablas toca |
|-----------|----------|-----------------|
| **list_branches(root_workflow_id)** | Devuelve todas las ramas (directas e indirectas) del workflow raíz. | `Workflow` (WHERE `root_branch = root_id`). |
| **merge_branch(source_exec_id, target_exec_id)** | Copia los snapshots del source a target, marcando los datos como “merged”. | `StepExecution`, `AbstractMolecularData` (crea nuevas versiones). |
| **revert_to_snapshot(exec_id, step_index)** | Crea una nueva rama cuyo `current_step_index` = `step_index`. | `WorkflowExecution`, `StepExecution`. |

### 6.4 Control de calidad y aprobaciones

- Cada `AbstractMolecularData` tiene `confidence_score` y `is_approved`.  
- Un *moderador* (usuario con permiso) puede **aprobar** un dato congelado → `is_approved=True`.  
- Los pasos que requieran datos aprobados pueden consultar `if not data.is_approved: raise …`.  

---

## 7⃣  Secuencia típica (paso a paso)

1. **Definir el workflow**  
   - Instanciar objetos `BaseStep` (ej. `DataAcquisitionStep`, `LogPCalculationStep`, `FilterStep`).  
   - Asignar `order` y establecer `required_/produced_`‑sets.  
   - Guardar el workflow (`Workflow.objects.create(...)`).  

2. **Crear la ejecución**  
   - `WorkflowExecution.objects.create(workflow=workflow)`.  
   - El motor crea el primer `StepExecution` con `status=PENDING`.  

3. **Ejecutar el primer paso**  
   - El motor llama `step.execute(step_execution, parameters)`.  
   - Dentro de `execute` se invoca `_process_step`.  
   - `_process_step` llama a los **providers** que correspondan (p. ej. `UserMoleculeSet.get_molecule_set()`).  
   - Los resultados se guardan como instancias de `AbstractMolecularData`.  
   - Cada instancia se **congela** automáticamente (`data.freeze(user)`).  

4. **Pasar al siguiente paso**  
   - El motor crea la siguiente `StepExecution`, tomando como `input_snapshot` los IDs de los datos congelados del paso anterior.  

5. **Branching (cuando el usuario cambia algo)**  
   - El UI detecta el cambio → llama a `workflow.branch(parameters, modified_step_id)`.  
   - El método:  
     - Copia la `Workflow` original → nueva `Workflow` (`branch_of = original`).  
     - Copia la `WorkflowExecution` actual → nueva `WorkflowExecution` (`parent_execution = current`).  
     - Copia **todos** los `StepExecution` previos (snapshot + resultados).  
     - Crea un nuevo `StepExecution` para el paso modificado con los nuevos parámetros.  

6. **Finalizar**  
   - Cuando el último paso se completa, la `WorkflowExecution` pasa a `COMPLETED`.  
   - El usuario puede **exportar** los resultados (p. ej. CSV de IDs de datos, JSON de los snapshots).  

---

## 8⃣  Diagrama de Clases (texto)

```
+-------------------+          +-----------------------+
|   Workflow        | 1 ---- * |   WorkflowExecution   |
+-------------------+          +-----------------------+
| id                |          | id                    |
| name              |          | workflow (FK)         |
| description       |          | status                |
| steps (ordered)   |          | current_step_index    |
| branch_of (FK)    |          | parent_execution (FK) |
| root_branch (FK)  |          +-----------------------+
+-------------------+                    |
            |                          |
            | *                        | *
            |                          |
+-------------------+          +-----------------------+
|   BaseStep        | 1 ---- * |   StepExecution       |
+-------------------+          +-----------------------+
| name              |          | id                    |
| description       |          | step (FK)             |
| order             |          | workflow_execution(FK)|
| required_*       |          | input_snapshot (JSON) |
| produced_*        |          | results (JSON)        |
| allows_branching  |          | status                |
+-------------------+          +-----------------------+

+-------------------+          +-----------------------+
|   AbstractMolecularData (ABC)  |
+-------------------+          |
| data_id (PK)      |          |
| molecule (FK)     |          |
| value_json        |          |
| native_type       |          |
| source, source_name, source_version |
| property_name     |          |
| provider_execution(FK) |
| is_frozen, frozen_at, frozen_by |
+-------------------+          |
            ^                 |
            |                 |
  +-------------------+  +-------------------+
  |   LogPData        |  |   ToxicityData   |
  +-------------------+  +-------------------+
  | get_native_type()|  | get_native_type()|
  | get_value_type() |  | get_value_type() |
  | serialize_value()|  | serialize_value()|
  | deserialize_value|  | deserialize_value|
  +-------------------+  +-------------------+

+-------------------+          +-----------------------+
| ProviderMoleculeSet (ABC) |    | ProviderPropertiesSet (ABC) |
+-------------------+          +-----------------------+
| get_molecule_set()|          | get_properties_set() |
+-------------------+          +-----------------------+
```

---

## 9⃣  Checklist de Implementación (para que no se te escape nada)

| Área | Tarea | Comentario |
|------|-------|------------|
| **Modelos** | Implementar `Molecule` y `AbstractMolecularData` con los métodos de (de)serialización. | Usa `json`/`orjson`; valida tipos con `isinstance`. |
| **Data Types** | Crear al menos dos tipos concretos (`LogPData`, `ToxicityData`). | Registra automáticamente en `SUBCLASS_REGISTRY`. |
| **Providers** | Implementar `ProviderMoleculeSet` y sus sub‑clases. | Cada sub‑clase debe devolver un `MoleculeSet` (lista de IDs). |
| **Providers de Propiedades** | Implementar `ProviderPropertiesSet` y sub‑clases que llamen a `AbstractMolecularData.retrieve_data`. | Cada provider debe crear **una** instancia de cada `produced_data_class`. |
| **Steps** | Definir `BaseStep` con `execute`, `_process_step`, `can_execute`, `get_progress`. | Usa `StepExecution.input_snapshot` y `StepExecution.results`. |
| **Workflows** | Definir `Workflow`, `WorkflowExecution`, `StepExecution`. | Asegúrate de que `branch_of` y `parent_execution` sean opcionales. |
| **Branching** | En `Workflow` añadir método `branch(modified_step_id, new_params)`. | Copia snapshots, crea nueva `Workflow` y `WorkflowExecution`. |
| **Freezing** | En `AbstractMolecularData` implementar `freeze(user)`. | Cada `ProviderExecution` debe llamar a `freeze` después de crear los datos. |
| **Auditoría** | Guardar `created_at`, `updated_at` en todos los modelos. | Usa `auto_now_add`/`auto_now`. |
| **Validación** | Definir JSON‑schema en `parameters_schema` de cada `Step`. | Los formularios UI pueden generar validaciones automáticas. |
| **Tests** | Unit tests para: <br>• congelación y error al modificar <br>• creación de rama y herencia de snapshots <br>• ejecución de workflow completo | Usa `pytest-django`. |
| **Documentación** | Generar diagramas de flujo y ejemplos de uso en README. | Incluye “how‑to create a new provider”. |

---

## 10⃣  Resumen rápido de los patrones aplicados

| Patrón | Donde se usa | Qué aporta |
|--------|--------------|------------|
| **Command** | Cada `BaseStep` (y sus sub‑clases). | Encapsula la acción, permite ejecutar, deshacer, volver a ejecutar. |
| **Memento** | `StepExecution.input_snapshot`, `AbstractMolecularData` (freeze). | Guardar estado inmutable para reproducibilidad. |
| **State** | `WorkflowExecution.status`, `StepExecution.status`. | Modelo explícito del ciclo de vida (pending → running → completed/failed). |
| **Builder** | Creación de `Workflow` con lista ordenada de `BaseStep`. | Facilita la construcción paso‑a‑paso del pipeline. |
| **Composite** | `Workflow` contiene varios `BaseStep` que a su vez pueden contener sub‑steps (p. ej. un `DataAcquisitionStep` que agrupa varios `ProviderPropertiesSet`). | Permite jerarquías arbitrarias de pasos. |
| **Observer (opcional)** | Señales Django (`post_save` de `AbstractMolecularData`) para disparar notificaciones o recomputar pasos dependientes. | Reactividad automática. |

---

## 11⃣  Qué clase debe existir (lista definitiva)

| Paquete | Clase (abstracta / concreta) |
|---------|------------------------------|
| **models** | `Molecule`, `AbstractMolecularData`, `ProviderExecution` (registro de cada run de provider), `Workflow`, `WorkflowExecution`, `StepExecution`, `Branch` (opcional, si quieres separar la lógica de árbol). |
| **data_types** | `LogPData`, `ToxicityData`, `SolubilityData`, `MolecularWeightData`, … (cualquiera que necesites). |
| **providers/molecule_sets** | `ProviderMoleculeSet` (abstracto), `UserMoleculeSet`, `TestMoleculeSet`, `AmbitMoleculeSet`, `ProToxMoleculeSet`, … |
| **providers/properties_set** | `ProviderPropertiesSet` (abstracto), `LogPProvider`, `ToxicityProvider`, `GaussianProvider`, `RDKitDescriptorProvider`, … |
| **workflows** | `BaseStep` (abstracto), `DataAcquisitionStep`, `CalculationStep`, `FilterStep`, `AnalysisStep`, `Workflow` (estructura), `WorkflowExecution`, `StepExecution`. |
| **utils** | `serializers.py` (funciones genéricas JSON ↔ Python), `validators.py` (JSON‑schema validator), `branching.py` (funciones para copiar snapshots y crear ramas). |

---

### Próximos pasos

1. **Escribe los tests de unidad** antes de codificar; con TDD tendrás la arquitectura ya validada.  
2. **Implementa primero los modelos** (`Molecule`, `AbstractMolecularData`) y verifica que la congelación funciona.  
3. **Crea un primer provider** (`UserMoleculeSet`) y un paso sencillo (`DataAcquisitionStep`).  
4. **Construye un workflow de ejemplo** (adquisición → cálculo logP → filtrado).  
5. **Prueba el branching** cambiando el parámetro de filtrado y verifica que se crea una nueva rama con los snapshots heredados.  

