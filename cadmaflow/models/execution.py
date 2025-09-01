"""WorkflowExecution model (separate module)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, cast

from django.db import models
from django.utils import timezone

from .choices import StatusChoices
from .workflow import WorkflowBranch

if TYPE_CHECKING:  # pragma: no cover
    from .step_execution import StepExecution


class WorkflowExecution(models.Model):
    """Ejecución concreta de un Workflow sobre familias de moléculas."""

    execution_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    workflow = models.ForeignKey('cadmaflow_models.Workflow', on_delete=models.CASCADE, related_name='executions')
    branch = models.ForeignKey('cadmaflow_models.WorkflowBranch', on_delete=models.CASCADE, related_name='executions')
    families = models.ManyToManyField('cadmaflow_models.MolecularFamily', related_name='executions')
    family_data_config = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    current_step = models.CharField(max_length=100, blank=True)
    current_step_index = models.IntegerField(default=0)
    parent_execution = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_executions')
    branch_label = models.CharField(max_length=100, blank=True)
    execution_results = models.JSONField(default=dict, blank=True)
    execution_metrics = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    # --- Typing helpers (no runtime effect) ---------------------------------
    if TYPE_CHECKING:  # pragma: no cover - aids static analyzers only
        # Reverse FK related managers injected by Django via related_name
        from django.db.models import Manager  # type: ignore

        from .events import WorkflowEvent  # noqa: WPS433
        from .selection import DataSelection  # noqa: WPS433
        from .step_execution import StepExecution  # noqa: WPS433

        step_executions: Manager['StepExecution']  # reverse of StepExecution.execution
        data_selections: Manager['DataSelection']  # reverse of DataSelection.execution
        events: Manager['WorkflowEvent']  # reverse of WorkflowEvent.execution

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.execution_id} - {self.name}"

    def set_data_retrieval_method(self, family_id: str, data_class_name: str, method: str) -> None:
        """Registra el método de obtención usado/forzado para una familia y clase de dato.

        Almacena una estructura tipo:
        family_data_config = {
            "FAM001": {"LogPData": "user_input", "ToxicityData": "user_input"},
            ...
        }
        Esto permite reproducir cómo se obtuvieron los datos o modificar preferencias
        antes de ejecutar pasos posteriores.
        """
        cfg = self.family_data_config
        fam_cfg = cfg.setdefault(family_id, {})
        fam_cfg[data_class_name] = method
        self.family_data_config = cfg
        self.save(update_fields=["family_data_config", "updated_at"]) if hasattr(self, 'updated_at') else self.save()

    def get_data_retrieval_method(self, family_id: str, data_class_name: str) -> str | None:
        """Devuelve el método previamente registrado para (familia, clase).

        Retorna None si no hay registro explícito. Usado por steps para decidir
        si deben recalcular o reutilizar variantes existentes.
        """
        return self.family_data_config.get(family_id, {}).get(data_class_name)

    def fork_execution(self, *, new_execution_id: str, target_branch: WorkflowBranch) -> 'WorkflowExecution':
        """Crea una nueva ejecución (fork) en otra rama manteniendo estado actual.

        Copia configuración de familias y vincula la ejecución original como parent.
        No clona StepExecution completados (eso se hace en `branch_execution` cuando
        la intención es duplicar historia completa). Aquí solo se crea un punto de
        partida limpio en la nueva rama.
        """
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

    def start_step(self, *, step_id: str, step_name: str, order: int,
                   frozen_snapshot: Dict[str, Any], retrieval_methods: Dict[str, Any]) -> 'StepExecution':
        """Inicia un step creando su StepExecution en estado RUNNING.

        frozen_snapshot: snapshot inmutable de entradas (IDs / valores) para reproducibilidad.
        retrieval_methods: mapping de (family_id -> {DataClass: method}) usado luego
        para auditoría y potencial branching.
        """
        from .step_execution import StepExecution  # local import
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

    def complete_step(self, step_exec: 'StepExecution', results: Dict[str, Any]) -> None:
        """Marca un StepExecution como COMPLETED y actualiza punteros de progreso.

        results debe ser JSON serializable (IDs de datos creados, métricas, etc.).
        Registra un evento para reconstruir timeline en UI / auditoría.
        """
        step_exec.results = results
        step_exec.status = StatusChoices.COMPLETED
        step_exec.completed_at = timezone.now()
        step_exec.save()
        self.current_step = step_exec.step_id
        self.current_step_index = step_exec.order + 1
        self.save(update_fields=["current_step", "current_step_index"])
        self.log_event(event_type="STEP_COMPLETED", details={"step_id": step_exec.step_id})

    def freeze_family_data(self) -> Dict[str, Dict[str, Dict[str, int]]]:  # simplificado
        """Crea un snapshot ligero de la composición (moléculas) por familia.

        Este snapshot no incluye valores de propiedades; se usa como base para
        steps que necesiten saber qué moléculas estaban presentes al inicio del
        step o para comparar divergencias tras branching.
        """
        snapshot: Dict[str, Dict[str, Dict[str, int]]] = {}
        for family in self.families.all():
            fam_block = snapshot.setdefault(family.family_id, {})
            for molecule in family.members.all():
                fam_block[molecule.inchikey] = {"id": molecule.id}
        return snapshot

    def log_event(self, *, event_type: str, details: Dict[str, Any] | None = None) -> None:
        """Log de evento simple anexado a la ejecución.

        Se modela como inserción append-only (WorkflowEvent) para permitir
        reconstruir la línea de tiempo y facilitar debugging de branching.
        """
        from .events import WorkflowEvent  # local import
        WorkflowEvent.objects.create(
            execution=self,
            event_type=event_type,
            details=details or {},
        )

    def timeline(self) -> List[Dict[str, Any]]:  # pragma: no cover
        # Avoid plugin internal error with values() TypedDict inference by casting.
        rows: Iterable[Dict[str, Any]] = self.events.order_by("created_at").values("event_type", "details", "created_at")  # type: ignore[no-untyped-call]
        return [cast(Dict[str, Any], r) for r in rows]

    def select_property_variant(self, *, molecule: Any, property_name: str,
                                data_instance: Any, user: Any | None = None) -> Any:
        """Selecciona (o actualiza) la variante activa de una propiedad para una molécula.

        Si ya existía un DataSelection se sobreescribe; se dispara detección automática
        de branching si la propiedad impacta steps completados.
        """
        from .selection import DataSelection
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

    def get_selected_property(self, *, molecule: Any, property_name: str) -> Any | None:  # -> object | None
        """Return selected data instance or None.

        Deliberately strict: if stored ``data_class`` no longer resolves to a
        registered concrete data model the selection is considered invalid and
        ``None`` is returned (instead of attempting heuristic scans). This
        keeps semantics predictable for callers and matches test expectations.
        """
        from .abstract_models import SUBCLASS_REGISTRY, get_data_class_by_name
        from .selection import DataSelection
        try:
            ds = DataSelection.objects.get(
                execution=self, branch=self.branch, molecule=molecule, property_name=property_name
            )
        except DataSelection.DoesNotExist:  # noqa: PERF203
            # Fallback: ignore branch (after forks/rewinds original selection should still count)
            ds = (
                DataSelection.objects.filter(
                    execution=self, molecule=molecule, property_name=property_name
                )
                .order_by('-selected_at')
                .first()
            )
            if not ds:
                return None
        cls = get_data_class_by_name(ds.data_class)  # type: ignore[arg-type]
        if not cls:
            return None
        try:
            return cls.objects.get(pk=ds.data_id)  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - defensive broad fallback
            # As a safety net (e.g. model renamed) scan all registered data classes.
            for _c in SUBCLASS_REGISTRY.values():
                inst = _c.objects.filter(pk=ds.data_id).first()  # type: ignore[attr-defined]
                if inst:
                    return inst
            return None

    def list_variants(self, *, molecule: Any, property_name: str) -> List[Any]:  # -> list[object]
        """Lista todas las variantes (instancias de datos) disponibles para la propiedad dada.

        Explora el registro de subclases en memoria (SUBCLASS_REGISTRY) sin consultar
        modelos no registrados, manteniendo determinismo.
        """
        from .abstract_models import SUBCLASS_REGISTRY
        variants = []
        for cls in SUBCLASS_REGISTRY.values():
            qs = cls.objects.filter(molecule=molecule, property_name=property_name)
            variants.extend(list(qs))
        return variants

    def _auto_fork_if_impacts_completed_steps(self, *, property_name: str, molecule: Any) -> None:
        """Genera automáticamente una rama si cambiar una selección afecta steps cerrados.

        Estrategia: inspeccionar StepExecution completados que declararon haber
        usado la propiedad (input_properties). Si existe impacto se crea:
            - nueva WorkflowBranch derivada
            - nueva WorkflowExecution (fork) con data selections clonadas
        Registrando evento AUTO_FORK para reconstrucción de historia.
        """
        from django.db import connection

        from .selection import DataSelection
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
        from django.utils import timezone as _tz
        suffix = _tz.now().strftime('%Y%m%d%H%M%S')
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

    def branch_execution(self, *, branch_label: str | None = None, reason: str | None = None) -> 'WorkflowExecution':  # -> 'WorkflowExecution'
        """Crea una nueva ejecución copiando todos los StepExecution completados.

        Diferente de `fork_execution` (que no clona pasos). Útil para branching
        explícito solicitado por el usuario o para rewind granular.
        """
        from django.utils import timezone as _tz

        from .step_execution import StepExecution
        new_wf = self.workflow.branch(branch_label=branch_label, reason=reason)
        ts = _tz.now().strftime('%H%M%S')
        # Use a short incrementing loop to avoid collisions within the same second in fast tests
        base_branch_id = f"{self.branch.branch_id}-br-{ts}"
        branch_candidate = base_branch_id
        i = 0
        from .workflow import WorkflowBranch as _WB
        while _WB.objects.filter(branch_id=branch_candidate).exists():  # pragma: no cover - rarely loops
            i += 1
            branch_candidate = f"{base_branch_id}-{i}"
        new_branch = self.branch.fork(new_branch_id=branch_candidate, name=new_wf.branch_label)
        base_exec_id = f"{self.execution_id}-br-{ts}"
        exec_candidate = base_exec_id
        while WorkflowExecution.objects.filter(execution_id=exec_candidate).exists():  # pragma: no cover
            i += 1
            exec_candidate = f"{base_exec_id}-{i}"
        new_exec_id = exec_candidate
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

    def rewind_to(self, *, step_order: int) -> 'WorkflowExecution':  # -> 'WorkflowExecution'
        """Crea una rama nueva rebobinada al estado inmediatamente después del step dado.

        Elimina de la ejecución resultante los StepExecution con orden mayor, permitiendo
        re-ejecutar a partir de ese punto manteniendo historia anterior intacta.
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
    def list_branch_executions(cls, root_workflow: Any) -> Any:  # pragma: no cover
        # Return type left as Any to avoid tight coupling with Django stubs internal invariance.
        return cls.objects.filter(workflow__root_branch=root_workflow.root_branch or root_workflow)
