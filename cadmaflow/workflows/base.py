"""Infraestructura base de Flujos (Workflows) de alto nivel.

Un Flow orquesta una secuencia ordenada de ``BaseStep``. El modelo persistente
(`WorkflowDefinition`, `WorkflowExecution`, etc.) vive en ``models`` pero esta
clase provee la API Python amigable para disparar steps en orden y manejar
ramas de manera declarativa.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Type

from cadmaflow.models.choices import StatusChoices
from cadmaflow.models.models import WorkflowExecution

from .steps import BaseStep


@dataclass(slots=True)
class FlowMeta:
    flow_id: str
    name: str
    description: str = ""


class FlowBase:
    """Clase base de flujos.

    Subclases deben definir:
    - meta: FlowMeta
    - steps: Sequence[Type[BaseStep]] (orden lógico)
    """

    meta: FlowMeta
    steps: Sequence[Type[BaseStep]] = ()

    def __init__(self, execution: WorkflowExecution):
        self.execution = execution

    # --- Orquestación principal -------------------------------------------------
    def run(self, *, until_step: str | None = None, auto_skip_completed: bool = True):
        """Ejecuta steps en orden.

        Args:
            until_step: si se especifica detiene después de ese step_id
            auto_skip_completed: si ya existe un StepExecution COMPLETED lo salta
        """
        ordered = sorted(self.steps, key=lambda cls: cls.order)
        for step_cls in ordered:
            if until_step and step_cls.step_id == until_step and self._is_completed(step_cls):
                break
            self._run_single_step(step_cls, auto_skip_completed=auto_skip_completed)
            if until_step and step_cls.step_id == until_step:
                break

    # --- Helpers ----------------------------------------------------------------
    def _is_completed(self, step_cls: Type[BaseStep]):
        return self.execution.step_executions.filter(step_id=step_cls.step_id, status=StatusChoices.COMPLETED).exists()

    def _run_single_step(self, step_cls: Type[BaseStep], *, auto_skip_completed: bool):
        if auto_skip_completed and self._is_completed(step_cls):
            return
        step_obj = step_cls()  # asume init sin args; subclases avanzadas pueden sobrescribir
        if not step_obj.can_execute(self.execution):
            raise RuntimeError(f"Step {step_cls.step_id} no puede ejecutarse: dependencias incompletas")
        # Congelar snapshot simple (puede ser extendido)
        snapshot = self.execution.freeze_family_data()
        retrieval_methods = self.execution.family_data_config
        step_exec = self.execution.start_step(
            step_id=step_cls.step_id,
            step_name=step_cls.name,
            order=step_cls.order,
            frozen_snapshot=snapshot,
            retrieval_methods=retrieval_methods,
        )
        try:
            results = step_obj.execute(step_exec, parameters={})
            self.execution.complete_step(step_exec, results)
        except Exception as exc:  # noqa: BLE001
            step_exec.mark_failed(str(exc))
            raise

    # --- Branching --------------------------------------------------------------
    def fork(self, *, new_execution_id: str, new_branch_id: str, name: str):
        branch = self.execution.branch.fork(new_branch_id=new_branch_id, name=name)
        return self.execution.fork_execution(new_execution_id=new_execution_id, target_branch=branch)
