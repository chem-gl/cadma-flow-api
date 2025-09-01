"""Infraestructura base de Flujos (Workflows) de alto nivel.

Un Flow orquesta una secuencia ordenada de ``BaseStep``. El modelo persistente
(`WorkflowDefinition`, `WorkflowExecution`, etc.) vive en ``models`` pero esta
clase provee la API Python amigable para disparar steps en orden y manejar
ramas de manera declarativa.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Type

from cadmaflow.models import WorkflowExecution
from cadmaflow.models.choices import StatusChoices

from .steps import BaseStep


@dataclass(slots=True)
class FlowMeta:
    """
    Metadatos descriptivos para un flujo (workflow).

    Uso típico:
        - Se utiliza para describir el flujo lógico, su identificador único, nombre y descripción.
        - Permite documentar y distinguir diferentes flujos en la plataforma.
    Ejemplo:
        FlowMeta(flow_id="screening", name="Screening QSAR", description="Flujo para predicción de propiedades QSAR")
    """
    flow_id: str  # Identificador único del flujo
    name: str     # Nombre legible para humanos
    description: str = ""  # Descripción opcional


class FlowBase:
    """
    Clase base para la definición de flujos (workflows) de alto nivel.

    Uso típico:
        - Se extiende para crear flujos concretos, definiendo los steps y metadatos.
        - Orquesta la ejecución secuencial de steps, maneja dependencias y ramificación.
        - Permite controlar el avance, saltar steps completados y crear ramas nuevas.

    Ejemplo de uso:
        class MyFlow(FlowBase):
            meta = FlowMeta(flow_id="myflow", name="Mi Flujo", description="Ejemplo de flujo personalizado")
            steps = (StepA, StepB, StepC)

        flow = MyFlow(execution)
        flow.run()
    """
    meta: FlowMeta  # Metadatos del flujo
    steps: Sequence[Type[BaseStep]] = ()  # Secuencia ordenada de steps

    def __init__(self, execution: WorkflowExecution):
        """
        Inicializa el flujo con la ejecución persistente asociada.
        execution: instancia de WorkflowExecution que representa el estado actual.
        """
        self.execution = execution

    def run(self, *, until_step: str | None = None, auto_skip_completed: bool = True):
        """
        Ejecuta los steps definidos en orden lógico.
        until_step: si se especifica, detiene después de ese step_id.
        auto_skip_completed: si un step ya está COMPLETED, lo salta automáticamente.
        """
        ordered = sorted(self.steps, key=lambda cls: cls.order)
        for step_cls in ordered:
            if until_step and step_cls.step_id == until_step and self._is_completed(step_cls):
                break
            self._run_single_step(step_cls, auto_skip_completed=auto_skip_completed)
            if until_step and step_cls.step_id == until_step:
                break

    def _is_completed(self, step_cls: Type[BaseStep]):
        """
        Verifica si el step dado ya está marcado como COMPLETED en la ejecución.
        step_cls: clase del step a verificar.
        """
        return self.execution.step_executions.filter(step_id=step_cls.step_id, status=StatusChoices.COMPLETED).exists()

    def _run_single_step(self, step_cls: Type[BaseStep], *, auto_skip_completed: bool):
        """
        Ejecuta un solo step, manejando dependencias y errores.
        auto_skip_completed: si el step ya está COMPLETED, lo salta.
        """
        if auto_skip_completed and self._is_completed(step_cls):
            return
        step_obj = step_cls()  # Se asume init sin args; subclases avanzadas pueden sobrescribir
        if not step_obj.can_execute(self.execution):
            raise RuntimeError(f"Step {step_cls.step_id} no puede ejecutarse: dependencias incompletas")
        # Congela un snapshot simple de los datos familiares
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
        except Exception as exc:
            step_exec.mark_failed(str(exc))
            raise

    def fork(self, *, new_execution_id: str, new_branch_id: str, name: str):
        """
        Crea una nueva rama (branch) y ejecución (execution) derivada de la actual.
        new_execution_id: identificador único para la nueva ejecución.
        new_branch_id: identificador único para la nueva rama.
        name: nombre descriptivo para la rama.
        Retorna la nueva ejecución creada.
        """
        branch = self.execution.branch.fork(new_branch_id=new_branch_id, name=name)
        return self.execution.fork_execution(new_execution_id=new_execution_id, target_branch=branch)
