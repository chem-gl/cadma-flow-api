# molecules/models.py
"""
Modelos concretos de la base de datos para el sistema de workflow molecular.
"""
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from .abstract_models import AbstractMolecularData
from .choices import StatusChoices
from .providers import (
    ProviderExecution,  # noqa: F401  -- ensure model registration for FK resolution
)

User = get_user_model()

class Molecule(models.Model):
    """
    Modelo para representar una molécula única.
    
    Propósito:
    - Almacenar la información fundamental de una molécula
    - Servir como punto central de referencia para todos los datos moleculares
    - Proporcionar identificadores únicos para la molécula (SMILES, InChI, InChIKey)
    
    Nota: Este modelo es la entidad central del sistema, todos los datos
    moleculares se relacionan con una instancia de Molecule.
    """
    
    # Identificadores únicos para la molécula
    smiles = models.TextField(unique=True)
    inchi = models.TextField(unique=True)
    inchikey = models.CharField(max_length=27, unique=True)
    
    # Información básica de la molécula
    molecular_formula = models.CharField(max_length=100)
    molecular_weight = models.FloatField()
    common_name = models.CharField(max_length=255, blank=True)
    
    # Banderas especiales
    is_reference = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.common_name or 'Molecule'} ({self.inchikey})"

    # --- Data helpers -------------------------------------------------
    def get_data(self, data_class: type[AbstractMolecularData], *, source: str | None = None,
                 user_tag: str | None = None):
        qs = data_class.objects.filter(molecule=self)
        if source:
            qs = qs.filter(source=source)
        if user_tag:
            qs = qs.filter(user_tag=user_tag)
        return qs

    def get_or_create_data(self, data_class: type[AbstractMolecularData], *, method: str,
                            config: dict | None = None, user_tag: str | None = None):
        existing = self.get_data(data_class, user_tag=user_tag)
        if existing.exists():
            return existing.first(), False
        instance = data_class.retrieve_data(self, method, config=config, user_tag=user_tag)
        return instance, True

    def ensure_all(self, data_reqs: list[tuple[type[AbstractMolecularData], str]], *,
                   config_map: dict | None = None):
        results = {}
        for cls, method in data_reqs:
            inst, _ = self.get_or_create_data(cls, method=method,
                                              config=(config_map or {}).get(cls.__name__))
            results[cls.__name__] = inst.data_id if inst else None
        return results


class WorkflowDefinition(models.Model):
    """Blueprint de un workflow (lista de steps y metadatos)."""
    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    # Lista ordenada de IDs de steps (referencia lógica)
    steps_sequence = models.JSONField(default=list, help_text="Orden lógico de steps (IDs)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # pragma: no cover - trivial
        return f"{self.key} - {self.name}"


class MolecularFamily(models.Model):
    """
    Grupo de moléculas relacionadas que se procesan juntas en un workflow.
    
    Propósito:
    - Agrupar moléculas relacionadas para procesamiento conjunto
    - Permitir el análisis comparativo entre familias moleculares
    - Facilitar la gestión de conjuntos de datos en el workflow
    
    Características:
    - Las familias pueden definirse específicamente para cada workflow
    - Pueden usarse como resultado de un paso del workflow
    - Tienen nombre y descripción para identificación clara
    """
    
    # Identificador y nombre de la familia
    family_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Relación many-to-many con las moléculas miembros
    members = models.ManyToManyField(Molecule, related_name="families")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.family_id} - {self.name}"


class WorkflowBranch(models.Model):
    """
    Representa una rama de ejecución del flujo de trabajo.
    
    Propósito:
    - Permitir diferentes caminos de ejecución dentro de un workflow
    - Gestionar selecciones específicas de datos para cada rama
    - Mantener el historial de bifurcaciones del workflow
    
    Características:
    - Cada rama puede tener su propia configuración de obtención de datos
    - Las ramas pueden tener una relación padre-hijo para tracking
    - Permiten experimentación con diferentes configuraciones
    """
    
    # Identificador único de la rama
    branch_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Relación con la definición del workflow
    workflow_definition = models.ForeignKey('WorkflowDefinition', on_delete=models.CASCADE,
                                          related_name='branches')
    
    # Relaciones de ramificación (para tracking de bifurcaciones)
    parent_branch = models.ForeignKey('self', on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='children')
    branch_reason = models.TextField(blank=True)
    
    # Preferencias de selección de datos para esta rama
    data_selection_preferences = models.JSONField(
        default=dict,
        help_text="Preferencias de selección de datos para esta rama"
    )
    
    # Estado de la rama
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.branch_id} - {self.name}"

    def fork(self, *, new_branch_id: str, name: str, reason: str | None = None,
             preference_overrides: dict | None = None):
        """Crea una nueva rama hija heredando preferencias."""
        data_prefs = dict(self.data_selection_preferences)
        if preference_overrides:
            data_prefs.update(preference_overrides)
        return WorkflowBranch.objects.create(
            branch_id=new_branch_id,
            name=name,
            description=self.description,
            workflow_definition=self.workflow_definition,
            parent_branch=self,
            branch_reason=reason,
            data_selection_preferences=data_prefs,
        )


class WorkflowExecution(models.Model):
    """
    Ejecución de un workflow para múltiples familias.
    
    Propósito:
    - Representar una instancia específica de ejecución de workflow
    - Gestionar el estado y progreso de la ejecución
    - Almacenar resultados y métricas de la ejecución
    
    Características:
    - Puede procesar múltiples familias moleculares simultáneamente
    - Mantiene relación con una rama específica del workflow
    - Registra configuración específica por familia
    """
    
    # Identificador único de la ejecución
    execution_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Relaciones con definición de workflow y rama
    workflow_definition = models.ForeignKey('WorkflowDefinition', on_delete=models.CASCADE,
                                          related_name='executions')
    branch = models.ForeignKey(WorkflowBranch, on_delete=models.CASCADE,
                             related_name='executions')
    
    # Familias moleculares procesadas en esta ejecución
    families = models.ManyToManyField(MolecularFamily, related_name='executions')
    
    # Configuración de obtención de datos por familia
    family_data_config = models.JSONField(
        default=dict,
        help_text="Configuración de métodos de obtención de datos por familia"
    )
    
    # Estado de la ejecución
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    current_step = models.CharField(max_length=100, blank=True)
    
    # Resultados y métricas
    execution_results = models.JSONField(default=dict, blank=True)
    execution_metrics = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.execution_id} - {self.name}"

    # --- Config helpers -----------------------------------------------
    def set_data_retrieval_method(self, family_id: str, data_class_name: str, method: str):
        cfg = self.family_data_config
        fam_cfg = cfg.setdefault(family_id, {})
        fam_cfg[data_class_name] = method
        self.family_data_config = cfg
        self.save(update_fields=["family_data_config", "updated_at"]) if hasattr(self, 'updated_at') else self.save()

    def get_data_retrieval_method(self, family_id: str, data_class_name: str) -> str | None:
        return self.family_data_config.get(family_id, {}).get(data_class_name)

    # --- Branching ----------------------------------------------------
    def fork_execution(self, *, new_execution_id: str, target_branch: 'WorkflowBranch'):
        """Clona esta ejecución en otra rama para explorar un camino alterno."""
        clone = WorkflowExecution.objects.create(
            execution_id=new_execution_id,
            name=self.name + f" (fork:{target_branch.branch_id})",
            description=self.description,
            workflow_definition=self.workflow_definition,
            branch=target_branch,
            family_data_config=self.family_data_config,
        )
        clone.families.set(self.families.all())
        clone.log_event(event_type="FORK", details={"from": self.execution_id, "to_branch": target_branch.branch_id})
        return clone

    # --- Step orchestration ------------------------------------------
    def start_step(self, *, step_id: str, step_name: str, order: int,
                   frozen_snapshot: dict, retrieval_methods: dict):
        return StepExecution.objects.create(
            execution=self,
            step_id=step_id,
            step_name=step_name,
            order=order,
            input_data_snapshot=frozen_snapshot,
            data_retrieval_methods=retrieval_methods,
            status=StatusChoices.RUNNING,
            started_at=timezone.now(),
            data_frozen_at=timezone.now(),
        )

    def complete_step(self, step_exec: 'StepExecution', results: dict):
        """Finaliza un step, guarda resultados y registra evento de trazabilidad."""
        step_exec.results = results
        step_exec.status = StatusChoices.COMPLETED
        step_exec.completed_at = timezone.now()
        step_exec.save()
        self.current_step = step_exec.step_id
        self.save(update_fields=["current_step"])  # lightweight update
        self.log_event(event_type="STEP_COMPLETED", details={"step_id": step_exec.step_id})

    def freeze_family_data(self):
        """Crea un snapshot simple de IDs de datos por molécula/familia (ejemplo)."""
        snapshot: dict = {}
        for family in self.families.all():
            fam_block = snapshot.setdefault(family.family_id, {})
            for molecule in family.members.all():
                fam_block[molecule.inchikey] = {"id": molecule.id}
        return snapshot

    # --- Traceability -------------------------------------------------
    def log_event(self, *, event_type: str, details: dict | None = None):
        WorkflowEvent.objects.create(
            execution=self,
            event_type=event_type,
            details=details or {},
        )

    def timeline(self):
        return list(self.events.order_by("created_at").values("event_type", "details", "created_at"))

    # --- Data selection (provider variants) -------------------------
    def select_property_variant(self, *, molecule: Molecule, property_name: str,
                                data_instance: AbstractMolecularData, user=None):
        """Crea o actualiza la selección activa de una propiedad para una molécula.

        No elimina variantes previas, sólo apunta a la escogida.
        """
        ds, created = DataSelection.objects.update_or_create(
            execution=self,
            branch=self.branch,
            molecule=molecule,
            property_name=property_name,
            defaults={
                'data_class': data_instance.__class__.__name__,
                'data_id': data_instance.data_id,
                'provider_execution': data_instance.provider_execution,
                'selected_by': user,
            }
        )
        self.log_event(event_type="DATA_SELECTION_CHANGED", details={
            "molecule": molecule.inchikey,
            "property": property_name,
            "data_class": ds.data_class,
            "data_id": str(ds.data_id),
            "created": created,
        })
        # Verificar si la propiedad impacta pasos anteriores y auto-fork si es necesario
        self._auto_fork_if_impacts_completed_steps(property_name=property_name, molecule=molecule)
        return ds

    def get_selected_property(self, *, molecule: Molecule, property_name: str) -> AbstractMolecularData | None:
        try:
            ds = DataSelection.objects.get(execution=self, branch=self.branch, molecule=molecule, property_name=property_name)
        except DataSelection.DoesNotExist:  # noqa: PERF203
            return None
        from .abstract_models import get_data_class_by_name
        cls = get_data_class_by_name(ds.data_class)
        if not cls:
            return None
        try:
            return cls.objects.get(pk=ds.data_id)
        except cls.DoesNotExist:  # type: ignore[attr-defined]
            return None

    def list_variants(self, *, molecule: Molecule, property_name: str):
        """Lista todas las variantes de datos disponibles para esa molécula y propiedad."""
        from .abstract_models import SUBCLASS_REGISTRY
        variants = []
        for cls in SUBCLASS_REGISTRY.values():
            qs = cls.objects.filter(molecule=molecule, property_name=property_name)
            variants.extend(list(qs))
        return variants

    # --- Internal helpers -------------------------------------------
    def _auto_fork_if_impacts_completed_steps(self, *, property_name: str, molecule: Molecule):
        """Si la selección modificada afecta un paso ya completado, crear una rama nueva.

        Estrategia:
        - Revisar StepExecution completados que incluyan la propiedad en input_properties.
        - Si alguno la incluye, crear nueva rama a partir de la actual (si no se creó ya en esta operación)
          y clonar esta ejecución en la nueva rama, preservando selección original en la rama vieja.
        - La nueva rama heredará todas las selecciones actuales (con el cambio) para continuar divergente.
        """
        impacted = self.step_executions.filter(status=StatusChoices.COMPLETED, input_properties__contains=[property_name])
        if not impacted.exists():
            return

        # Crear nueva rama
        suffix = timezone.now().strftime('%Y%m%d%H%M%S')
        new_branch_id = f"{self.branch.branch_id}-var-{suffix}"
        new_branch = self.branch.fork(new_branch_id=new_branch_id, name=f"Variant {suffix}")

        # Clonar ejecución
        new_exec_id = f"{self.execution_id}-var-{suffix}"
        new_exec = self.fork_execution(new_execution_id=new_exec_id, target_branch=new_branch)

        # Clonar selecciones existentes hacia la nueva ejecución (incluye la modificación ya hecha)
        for sel in self.data_selections.all():
            DataSelection.objects.create(
                execution=new_exec,
                branch=new_branch,
                molecule=sel.molecule,
                property_name=sel.property_name,
                data_class=sel.data_class,
                data_id=sel.data_id,
                provider_execution=sel.provider_execution,
                selected_by=sel.selected_by,
            )
        self.log_event(event_type="AUTO_FORK", details={
            "property": property_name,
            "new_branch": new_branch.branch_id,
            "new_execution": new_exec.execution_id,
        })
        # Nota: La nueva ejecución aún no tiene StepExecutions; se recalcularán pasos según necesidad.


class StepExecution(models.Model):
    """
    Registra la ejecución de un paso específico en un workflow.
    
    Propósito:
    - Trackear la ejecución individual de cada paso del workflow
    - Almacenar snapshot de los datos utilizados (que se congelan)
    - Mantener metadata sobre métodos de obtención utilizados
    
    Características:
    - Congela los datos de entrada utilizados en el paso
    - Registra los métodos de obtención utilizados para cada tipo de dato
    - Permite reproducir exactamente el paso con los mismos datos
    """
    
    # Relación con la ejecución de workflow
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE,
                                related_name='step_executions')
    
    # Identificación del paso
    step_id = models.CharField(max_length=100)
    step_name = models.CharField(max_length=200)
    order = models.IntegerField()
    
    # Snapshot de datos de entrada utilizados (congelados)
    input_data_snapshot = models.JSONField(
        default=dict,
        help_text="Snapshot de los datos de entrada utilizados en este paso"
    )
    
    # Métodos de obtención utilizados
    data_retrieval_methods = models.JSONField(
        default=dict,
        help_text="Métodos de obtención utilizados para cada tipo de dato"
    )
    
    # Resultados del paso
    results = models.JSONField(default=dict, blank=True)
    
    # Estado del paso
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    
    # Timestamps
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    data_frozen_at = models.DateTimeField(blank=True, null=True)
    # Firma de entradas para detección de divergencias
    input_signature = models.CharField(max_length=64, blank=True, help_text="SHA256 de entradas + parámetros + providers")
    # Lista de propiedades usadas como entrada
    input_properties = models.JSONField(default=list, blank=True)
    # Providers usados (ids de ProviderExecution) para reproducibilidad
    providers_used = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['order', 'started_at']
    
    def __str__(self):
        return f"{self.execution.execution_id} - {self.step_name} ({self.status})"

    def mark_failed(self, message: str):
        self.status = StatusChoices.FAILED
        self.results = {"error": message}
        self.completed_at = timezone.now()
        self.save()
        self.execution.log_event(event_type="STEP_FAILED", details={"step_id": self.step_id, "error": message})


class WorkflowEvent(models.Model):
    """Evento de trazabilidad asociado a una ejecución de workflow."""
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50, help_text="Tipo lógico del evento (STEP_COMPLETED, FORK, etc.)")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["execution", "event_type"]),
        ]

    def __str__(self):  # pragma: no cover - trivial
        return f"{self.execution.execution_id}:{self.event_type}@{self.created_at.isoformat()}"


class DataSelection(models.Model):
    """Selección activa de una variante de dato (por propiedad) en una ejecución y rama.

    Permite que cada propiedad tenga múltiples variantes producidas por distintos providers
    conservando sólo un puntero a la variante "activa" usada para steps posteriores.
    """

    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="data_selections")
    branch = models.ForeignKey(WorkflowBranch, on_delete=models.CASCADE, related_name="data_selections")
    molecule = models.ForeignKey(Molecule, on_delete=models.CASCADE, related_name="data_selections")
    property_name = models.CharField(max_length=100)
    data_class = models.CharField(max_length=150)
    data_id = models.UUIDField()
    provider_execution = models.ForeignKey('ProviderExecution', on_delete=models.SET_NULL, null=True, blank=True)
    selected_at = models.DateTimeField(auto_now_add=True)
    selected_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('execution', 'branch', 'molecule', 'property_name')
        indexes = [
            models.Index(fields=['molecule', 'property_name']),
            models.Index(fields=['property_name', 'provider_execution']),
        ]

    def __str__(self):  # pragma: no cover - trivial
        return f"Sel:{self.property_name} -> {self.data_class}({self.data_id})"