"""Base step abstraction moved from models.steps to workflows.steps.base.

This aligns with the README architecture where steps live under workflows/steps.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional, Sequence, Type

from django.utils import timezone

from cadmaflow.models.choices import StatusChoices
from cadmaflow.utils.types import JSONDict, JSONValue


class BaseStep(ABC):
    """
    Clase abstracta base para todos los steps de workflow.

    Uso típico:
        - Se extiende para crear steps concretos, definiendo identificador, nombre, descripción y orden.
        - Permite declarar dependencias de conjuntos moleculares y tipos de datos requeridos/producidos.
        - Provee métodos para preparar, ejecutar y verificar el avance del step.

    Ejemplo de uso:
        class MyStep(BaseStep):
            step_id = "step_a"
            name = "Primer paso"
            description = "Ejemplo de step personalizado"
            order = 1
            required_data_classes = (LogPData,)
            produced_data_classes = (ToxicityData,)
            def _process_step(self, input_data, step_execution, parameters):
                # lógica de procesamiento
                return {...}
    """
    step_id: str  # Identificador lógico único dentro del flujo (estable)
    name: str  # Nombre legible para humanos
    description: str  # Explicación breve del propósito del step
    order: int  # Posición lógica (usado para ordenar; no necesariamente contiguo)

    required_molecule_sets: Sequence[Type] = ()  # Providers que deben haber producido conjuntos moleculares
    produced_molecule_sets: Sequence[Type] = ()  # Providers que este step producirá
    required_data_classes: Sequence[Type] = ()  # Clases AbstractMolecularData requeridas como input
    produced_data_classes: Sequence[Type] = ()  # Clases de datos producidas/transformadas por este step

    allows_branching: bool = True  # Si es True, cambios de parámetros pueden crear una nueva rama
    parameters_schema: Dict[str, JSONValue] = {}  # Estructura tipo JSON schema para los parámetros aceptados

    def prepare(self, step_execution: object, parameters: Dict[str, JSONValue]) -> None:
        """
        Prepara el step antes de ejecutar. Puede ser sobreescrito por subclases.
        step_execution: instancia de StepExecution (o compatible)
        parameters: parámetros de configuración para el step
        Uso típico:
            - Validar parámetros, inicializar recursos, preparar contexto.
            - Por defecto no hace nada, pero subclases pueden extenderlo.
        """
        return None

    def execute(self, step_execution: object, parameters: Optional[Dict[str, JSONValue]] = None) -> JSONValue:
        """
        Ejecuta el step y retorna los resultados (JSONValue).
        step_execution: instancia de StepExecution (o compatible)
        parameters: parámetros de configuración para el step
        Uso típico:
            - Llama a prepare() para inicializar el contexto.
            - Ejecuta la lógica principal mediante _process_step().
            - Marca el step como COMPLETED y almacena los resultados.
        Subclases sólo necesitan implementar _process_step(); este método maneja la orquestación.
        """
        input_data = step_execution.input_data_snapshot
        parameters = parameters or {}
        self.prepare(step_execution, parameters)
        results = self._process_step(input_data, step_execution, parameters)
        step_execution.results = results
        step_execution.status = StatusChoices.COMPLETED
        step_execution.completed_at = timezone.now()
        step_execution.save(update_fields=["results", "status", "completed_at"])
        return results

    @abstractmethod
    def _process_step(self, input_data: JSONDict, step_execution: object, parameters: Dict[str, JSONValue]) -> JSONValue:
        """
        Procesa el step concreto. Debe ser implementado por subclases.
        input_data: snapshot de entrada
        step_execution: instancia de StepExecution (o compatible)
        parameters: parámetros de configuración
        Uso típico:
            - Implementar la lógica principal del step.
            - Retornar los resultados en formato JSONValue.
        """
        raise NotImplementedError

    def can_execute(self, execution: object) -> bool:
        """
        Verifica si el step puede ejecutarse (dependencias satisfechas).
        execution: instancia de WorkflowExecution (o compatible)
        Uso típico:
            - Revisa que todas las familias y miembros tengan los datos requeridos.
            - Retorna True si todas las dependencias están presentes, False en caso contrario.
        """
        for family in execution.families.all():
            for data_class in self.required_data_classes:
                for _ in family.members.all():
                    method = execution.get_data_retrieval_method(family.family_id, data_class.__name__)
                    if not method:
                        return False
        return True

    def get_progress(self, execution: object) -> float:
        """
        Calcula el progreso del step (proporción de datos requeridos presentes).
        execution: instancia de WorkflowExecution (o compatible)
        Uso típico:
            - Retorna un valor entre 0 y 1 indicando el porcentaje de datos requeridos presentes.
            - Útil para mostrar avance en interfaces gráficas o reportes.
        """
        total_required = 0
        completed = 0
        for family in execution.families.all():
            for _ in family.members.all():
                for data_class in self.required_data_classes:
                    total_required += 1
                    method = execution.get_data_retrieval_method(family.family_id, data_class.__name__)
                    if method:
                        completed += 1
        return completed / total_required if total_required else 1.0
