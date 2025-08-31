# molecules/models.py
"""Modelos concretos de la base de datos para el sistema de workflow molecular.

Este archivo define los modelos persistentes de dominio que sustentan:
- Entidades químicas básicas (Molecule)
- Agrupaciones (MolecularFamily)
- Definición (Workflow) y ramificación lógica (WorkflowBranch)
- Ejecuciones (WorkflowExecution) y snapshots de pasos (StepExecution)
- Eventos de trazabilidad (WorkflowEvent)
- Selección activa de variantes de propiedades (DataSelection)

Se añaden docstrings detallados alineados con la especificación del README.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

# Ensure provider models register before migration autodetector runs
from . import providers  # noqa: F401
from .abstract_models import AbstractMolecularData
from .choices import StatusChoices

User = get_user_model()


# ---------------------------------------------------------------------------
# Workflow (Blueprint lógico)
# ---------------------------------------------------------------------------
class Workflow(models.Model):
    """Blueprint lógico de un flujo.

    Responsabilidades:
    - Identificador reutilizable (``key``) y metadatos (``name``/``description``)
    - Estado global simple (``status``)
    - Relaciones de branching entre definiciones (``branch_of`` / ``root_branch``)
    - Punto de anclaje para ejecuciones concretas (``WorkflowExecution``)
    - Posible congelación lógica (freeze) para impedir cambios accidentales

    NOTA: La secuencia de steps no se almacena todavía; la orquestación vive en
    clases Python (``FlowBase``). Podría añadirse un campo JSON si se requiere
    persistir configuración dinámica.
    """

    key = models.CharField(max_length=50, unique=True, help_text="Identificador estable para referenciar el workflow")
    name = models.CharField(max_length=100, help_text="Nombre legible del workflow")
    description = models.TextField(blank=True, help_text="Descripción funcional / propósito")

    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)

    branch_of = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_branches',
        help_text="Workflow padre del que se bifurca esta definición"
    )
    root_branch = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='descendants',
        help_text="Workflow raíz del árbol al que pertenece esta rama"
    )
    branch_label = models.CharField(max_length=100, blank=True, help_text="Etiqueta legible de la rama (ej: 'v2-high-temp')")

    frozen_at = models.DateTimeField(null=True, blank=True, help_text="Momento en que se congeló la definición (inmutable)")
    frozen_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='frozen_workflows', help_text="Usuario que congeló la definición")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["branch_of"]),
            models.Index(fields=["root_branch"]),
        ]

    def save(self, *args, **kwargs):  # pragma: no cover
        if self.pk is None and self.branch_of and not self.root_branch:
            self.root_branch = self.branch_of.root_branch or self.branch_of
        super().save(*args, **kwargs)

    def freeze(self, user):  # pragma: no cover
        """Congelar la definición para evitar cambios lógicos (soft lock)."""
        self.frozen_at = timezone.now()
        self.frozen_by = user
        self.save(update_fields=["frozen_at", "frozen_by", "updated_at"])

    def branch(self, *, branch_label: str | None = None, reason: str | None = None, user=None) -> 'Workflow':
        """Crear una nueva rama (blueprint hijo) de este workflow.

        Args:
            branch_label: Etiqueta legible (autogenerada si no se proporciona).
            reason: Texto opcional de justificación (no persistido actualmente).
            user: Usuario que inicia la rama (reservado para auditoría futura).
        Returns:
            Workflow: nueva instancia hija.
        """
        new_wf = Workflow.objects.create(
            key=f"{self.key}-br-{int(timezone.now().timestamp())}",
            name=self.name,
            description=self.description,
            status=StatusChoices.PENDING,
            branch_of=self,
            root_branch=self.root_branch or self,
            branch_label=branch_label or f"branch-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        )
        # reason podría registrarse en un WorkflowEvent futuro
        return new_wf

    def __str__(self):  # pragma: no cover
        return f"WF:{self.key} - {self.name}"


# ---------------------------------------------------------------------------
# Molecule
# ---------------------------------------------------------------------------
class Molecule(models.Model):
    """Entidad central que representa una molécula única."""

    smiles = models.TextField(unique=True)
    inchi = models.TextField(unique=True)
    inchikey = models.CharField(max_length=27, unique=True)
    common_name = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # pragma: no cover
        return f"{self.common_name or 'Molecule'} ({self.inchikey})"

    # --- Data helpers -------------------------------------------------
    def get_data(self, data_class: type[AbstractMolecularData], *, source: str | None = None,
                 user_tag: str | None = None):
        """Obtener QuerySet filtrado de instancias de datos para esta molécula."""
        qs = data_class.objects.filter(molecule=self)
        if source:
            qs = qs.filter(source=source)
        if user_tag:
            qs = qs.filter(user_tag=user_tag)
        return qs

    def get_or_create_data(self, data_class: type[AbstractMolecularData], *, method: str,
                            config: dict | None = None, user_tag: str | None = None):
        """Recuperar (o crear) un dato usando el método de obtención indicado."""
        existing = self.get_data(data_class, user_tag=user_tag)
        if existing.exists():
            return existing.first(), False
        instance = data_class.retrieve_data(self, method, config=config, user_tag=user_tag)
        return instance, True

    def ensure_all(self, data_reqs: list[tuple[type[AbstractMolecularData], str]], *,
                   config_map: dict | None = None):
        """Garantizar existencia de cada (Clase, método) retornando sus UUID."""
        results: dict[str, str | None] = {}
        for cls, method in data_reqs:
            inst, _ = self.get_or_create_data(cls, method=method,
                                              config=(config_map or {}).get(cls.__name__))
            results[cls.__name__] = str(inst.data_id) if inst else None
        return results


# ---------------------------------------------------------------------------
# MolecularFamily
# ---------------------------------------------------------------------------
class MolecularFamily(models.Model):
    """Agrupa moléculas relacionadas para procesamiento conjunto."""

    family_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    members = models.ManyToManyField(Molecule, related_name="families")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # pragma: no cover
        return f"{self.family_id} - {self.name}"


# ---------------------------------------------------------------------------
# WorkflowBranch
# ---------------------------------------------------------------------------
class WorkflowBranch(models.Model):
    """Rama lógica para selección de variantes de datos dentro de un workflow."""

    branch_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    workflow = models.ForeignKey('cadmaflow_models.Workflow', on_delete=models.CASCADE,
                                 related_name='branches', help_text="Workflow blueprint al que pertenece la rama")

    parent_branch = models.ForeignKey('self', on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='children')
    branch_reason = models.TextField(blank=True)

    data_selection_preferences = models.JSONField(default=dict, help_text="Preferencias de selección de datos para esta rama")

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # pragma: no cover
        return f"{self.branch_id} - {self.name}"

    def fork(self, *, new_branch_id: str, name: str, reason: str | None = None,
             preference_overrides: dict | None = None):
        """Crear rama hija heredando preferencias (con overrides opcionales)."""
        prefs = dict(self.data_selection_preferences)
        if preference_overrides:
            prefs.update(preference_overrides)
        return WorkflowBranch.objects.create(
            branch_id=new_branch_id,
            name=name,
            description=self.description,
            workflow=self.workflow,
            parent_branch=self,
            branch_reason=reason or "",
            data_selection_preferences=prefs,
        )


# ---------------------------------------------------------------------------
# WorkflowExecution
# ---------------------------------------------------------------------------
class WorkflowExecution(models.Model):
    """Ejecución concreta de un Workflow sobre familias de moléculas."""

    execution_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    workflow = models.ForeignKey('cadmaflow_models.Workflow', on_delete=models.CASCADE,
                                 related_name='executions', help_text="Workflow blueprint de esta ejecución")
    branch = models.ForeignKey(WorkflowBranch, on_delete=models.CASCADE, related_name='executions')

    families = models.ManyToManyField(MolecularFamily, related_name='executions')

    family_data_config = models.JSONField(default=dict, help_text="Configuración de métodos de obtención por familia")

    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    current_step = models.CharField(max_length=100, blank=True)
    current_step_index = models.IntegerField(default=0)
    parent_execution = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='child_executions')
    branch_label = models.CharField(max_length=100, blank=True)

    execution_results = models.JSONField(default=dict, blank=True)
    execution_metrics = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):  # pragma: no cover
        return f"{self.execution_id} - {self.name}"

    # ---------------- Configuración de métodos -----------------------
    def set_data_retrieval_method(self, family_id: str, data_class_name: str, method: str):
        """Registrar método de obtención (se guarda en ``family_data_config``)."""
        cfg = self.family_data_config
        fam_cfg = cfg.setdefault(family_id, {})
        fam_cfg[data_class_name] = method
        self.family_data_config = cfg
        self.save(update_fields=["family_data_config", "updated_at"]) if hasattr(self, 'updated_at') else self.save()

    def get_data_retrieval_method(self, family_id: str, data_class_name: str) -> str | None:
        """Obtener método configurado para la combinación (familia, clase)."""
        return self.family_data_config.get(family_id, {}).get(data_class_name)

    # ---------------- Branching sencillo -----------------------------
    def fork_execution(self, *, new_execution_id: str, target_branch: WorkflowBranch):
        """Clonar ejecución hacia otra rama (sin clonar StepExecutions)."""
        clone = WorkflowExecution.objects.create(
            execution_id=new_execution_id,
            name=self.name + f" (fork:{target_branch.branch_id})",
            description=self.description,
            workflow=self.workflow,
            branch=target_branch,
            family_data_config=self.family_data_config,
            parent_execution=self,
            branch_label=target_branch.branch_id,
        )
        clone.families.set(self.families.all())
        clone.log_event(event_type="FORK", details={"from": self.execution_id, "to_branch": target_branch.branch_id})
        return clone

    # ---------------- Orquestación de steps --------------------------
    def start_step(self, *, step_id: str, step_name: str, order: int,
                   frozen_snapshot: dict, retrieval_methods: dict):
        """Crear registro StepExecution RUNNING con snapshot congelado de entrada."""
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
        """Marcar un step como COMPLETED y avanzar punteros de ejecución."""
        step_exec.results = results
        step_exec.status = StatusChoices.COMPLETED
        step_exec.completed_at = timezone.now()
        step_exec.save()
        self.current_step = step_exec.step_id
        self.current_step_index = step_exec.order + 1
        self.save(update_fields=["current_step", "current_step_index"])
        self.log_event(event_type="STEP_COMPLETED", details={"step_id": step_exec.step_id})

    def freeze_family_data(self):  # simplificado
        """Snapshot simple: {family_id: {inchikey: {id}}}. Extensible para propiedades."""
        snapshot: dict = {}
        for family in self.families.all():
            fam_block = snapshot.setdefault(family.family_id, {})
            for molecule in family.members.all():
                fam_block[molecule.inchikey] = {"id": molecule.id}
        return snapshot

    # ---------------- Trazabilidad -----------------------------------
    def log_event(self, *, event_type: str, details: dict | None = None):
        """Registrar evento de ejecución (append-only)."""
        WorkflowEvent.objects.create(
            execution=self,
            event_type=event_type,
            details=details or {},
        )

    def timeline(self):  # pragma: no cover
        """Recuperar eventos ordenados cronológicamente (lista de dicts)."""
        return list(self.events.order_by("created_at").values("event_type", "details", "created_at"))

    # ---------------- Selección de variantes -------------------------
    def select_property_variant(self, *, molecule: Molecule, property_name: str,
                                data_instance: AbstractMolecularData, user=None):
        """Crear/actualizar selección activa de una propiedad para la molécula.

        Tras actualizar, dispara lógica de auto-fork si la propiedad afectó
        pasos ya completados.
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
        self._auto_fork_if_impacts_completed_steps(property_name=property_name, molecule=molecule)
        return ds

    def get_selected_property(self, *, molecule: Molecule, property_name: str) -> AbstractMolecularData | None:
        """Obtener instancia de dato actualmente seleccionada (o None)."""
        try:
            ds = DataSelection.objects.get(execution=self, branch=self.branch, molecule=molecule, property_name=property_name)
        except DataSelection.DoesNotExist:  # noqa: PERF203
            return None
        from .abstract_models import get_data_class_by_name
        cls = get_data_class_by_name(ds.data_class)  # type: ignore[arg-type]
        if not cls:
            return None
        try:
            return cls.objects.get(pk=ds.data_id)
        except cls.DoesNotExist:  # type: ignore[attr-defined]
            return None

    def list_variants(self, *, molecule: Molecule, property_name: str):
        """Listar todas las variantes persistidas para la propiedad dada."""
        from .abstract_models import SUBCLASS_REGISTRY
        variants = []
        for cls in SUBCLASS_REGISTRY.values():
            qs = cls.objects.filter(molecule=molecule, property_name=property_name)
            variants.extend(list(qs))
        return variants

    # ---------------- Helpers internos --------------------------------
    def _auto_fork_if_impacts_completed_steps(self, *, property_name: str, molecule: Molecule):
        """Crear nueva rama si el cambio impacta pasos ya completados.

        Heurística básica: si algún StepExecution COMPLETED contiene la
        propiedad en ``input_properties`` se crea fork. Pensado para pruebas.
        """
        from django.db import connection
        try:
            if connection.features.supports_json_field_contains:  # type: ignore[attr-defined]
                impacted_exists = self.step_executions.filter(
                    status=StatusChoices.COMPLETED,
                    input_properties__contains=[property_name],
                ).exists()
            else:  # pragma: no cover
                raise AttributeError
        except Exception:  # noqa: BLE001
            impacted_exists = any(
                property_name in (se.input_properties or [])
                for se in self.step_executions.filter(status=StatusChoices.COMPLETED)
            )
        if not impacted_exists:
            return
        suffix = timezone.now().strftime('%Y%m%d%H%M%S')
        new_branch_id = f"{self.branch.branch_id}-var-{suffix}"
        new_branch = self.branch.fork(new_branch_id=new_branch_id, name=f"Variant {suffix}")
        new_exec_id = f"{self.execution_id}-var-{suffix}"
        new_exec = self.fork_execution(new_execution_id=new_exec_id, target_branch=new_branch)
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

    # ---------------- Branching / Rewind API -------------------------
    def branch_execution(self, *, branch_label: str | None = None, reason: str | None = None) -> 'WorkflowExecution':
        """Crear nueva ejecución (rama) clonando snapshots COMPLETED existentes."""
        new_wf = self.workflow.branch(branch_label=branch_label, reason=reason)
        new_branch = self.branch.fork(new_branch_id=f"{self.branch.branch_id}-br-{timezone.now().strftime('%H%M%S')}",
                                      name=new_wf.branch_label)
        new_exec_id = f"{self.execution_id}-br-{timezone.now().strftime('%H%M%S')}"
        new_exec = WorkflowExecution.objects.create(
            execution_id=new_exec_id,
            name=self.name,
            description=self.description,
            workflow=new_wf,
            branch=new_branch,
            family_data_config=self.family_data_config,
            status=StatusChoices.PENDING,
            parent_execution=self,
            branch_label=new_wf.branch_label,
        )
        new_exec.families.set(self.families.all())
        for se in self.step_executions.filter(status=StatusChoices.COMPLETED).order_by('order'):
            StepExecution.objects.create(
                execution=new_exec,
                step_id=se.step_id,
                step_name=se.step_name,
                order=se.order,
                input_data_snapshot=se.input_data_snapshot,
                data_retrieval_methods=se.data_retrieval_methods,
                results=se.results,
                status=StatusChoices.COMPLETED,
                started_at=se.started_at,
                completed_at=se.completed_at,
                data_frozen_at=se.data_frozen_at,
                input_signature=se.input_signature,
                input_properties=se.input_properties,
                providers_used=se.providers_used,
            )
        new_exec.current_step_index = self.current_step_index
        new_exec.save(update_fields=["current_step_index"])
        self.log_event(event_type="EXEC_BRANCH_CREATED", details={"new_execution": new_exec.execution_id})
        return new_exec

    def rewind_to(self, *, step_order: int) -> 'WorkflowExecution':
        """Crear rama truncada para re-ejecutar desde ``step_order``.

        Copia snapshots hasta ese orden (inclusive) y elimina posteriores en la
        nueva ejecución, avanzando el puntero para recomputar.
        """
        new_exec = self.branch_execution(branch_label=f"rewind-to-{step_order}")
        new_exec.step_executions.filter(order__gt=step_order).delete()
        new_exec.current_step_index = step_order + 1
        new_exec.save(update_fields=["current_step_index"])
        self.log_event(event_type="REWIND", details={
            "from_execution": self.execution_id,
            "rewind_to": step_order,
            "new_execution": new_exec.execution_id,
        })
        return new_exec

    @classmethod
    def list_branch_executions(cls, root_workflow: Workflow):  # pragma: no cover
        """Listar ejecuciones pertenecientes al árbol del workflow raíz."""
        return cls.objects.filter(workflow__root_branch=root_workflow.root_branch or root_workflow)


# ---------------------------------------------------------------------------
# StepExecution
# ---------------------------------------------------------------------------
class StepExecution(models.Model):
    """Snapshot/Memento de la ejecución de un paso dentro de un workflow."""

    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='step_executions')

    step_id = models.CharField(max_length=100)
    step_name = models.CharField(max_length=200)
    order = models.IntegerField()

    input_data_snapshot = models.JSONField(default=dict, help_text="Snapshot congelado de entradas (moléculas/propiedades)")
    data_retrieval_methods = models.JSONField(default=dict, help_text="Métodos de obtención usados")
    results = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)

    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    data_frozen_at = models.DateTimeField(blank=True, null=True)

    input_signature = models.CharField(max_length=64, blank=True, help_text="SHA256 de entradas + parámetros")
    input_properties = models.JSONField(default=list, blank=True)
    providers_used = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['order', 'started_at']

    def __str__(self):  # pragma: no cover
        return f"{self.execution.execution_id} - {self.step_name} ({self.status})"

    def mark_failed(self, message: str):
        """Marcar el step como FALLIDO y registrar el error en resultados."""
        self.status = StatusChoices.FAILED
        self.results = {"error": message}
        self.completed_at = timezone.now()
        self.save()
        self.execution.log_event(event_type="STEP_FAILED", details={"step_id": self.step_id, "error": message})

    # Alias compatibilidad (input_snapshot) ---------------------------------
    @property
    def input_snapshot(self):  # pragma: no cover
        return self.input_data_snapshot

    @input_snapshot.setter
    def input_snapshot(self, value):  # pragma: no cover
        self.input_data_snapshot = value


# ---------------------------------------------------------------------------
# WorkflowEvent
# ---------------------------------------------------------------------------
class WorkflowEvent(models.Model):
    """Evento de trazabilidad asociado a una ejecución (append-only)."""

    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50, help_text="Tipo lógico del evento (STEP_COMPLETED, FORK, etc.)")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["execution", "event_type"]),
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.execution.execution_id}:{self.event_type}@{self.created_at.isoformat()}"


# ---------------------------------------------------------------------------
# DataSelection
# ---------------------------------------------------------------------------
class DataSelection(models.Model):
    """Selección activa de variante de propiedad dentro de una ejecución y rama.
    Permite múltiples variantes coexistentes apuntando una sola como activa
    para pasos posteriores.
    """

    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="data_selections")
    branch = models.ForeignKey(WorkflowBranch, on_delete=models.CASCADE, related_name="data_selections")
    molecule = models.ForeignKey(Molecule, on_delete=models.CASCADE, related_name="data_selections")
    property_name = models.CharField(max_length=100)
    data_class = models.CharField(max_length=150)
    data_id = models.UUIDField()
    provider_execution = models.ForeignKey('cadmaflow_models.ProviderExecution', on_delete=models.SET_NULL, null=True, blank=True)
    selected_at = models.DateTimeField(auto_now_add=True)
    selected_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('execution', 'branch', 'molecule', 'property_name')
        indexes = [
            models.Index(fields=['molecule', 'property_name']),
            models.Index(fields=['property_name', 'provider_execution']),
        ]

    def __str__(self):  # pragma: no cover
        return f"Sel:{self.property_name} -> {self.data_class}({self.data_id})"