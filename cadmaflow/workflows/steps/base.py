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
    """Abstract base class for all workflow steps.

    Responsibilities:
    - Define the common interface
    - Provide execution template method
    - Manage dependency declarations
    """
    step_id: str  # Unique logical identifier inside the flow (stable)
    name: str  # Human friendly name
    description: str  # Short explanation of the purpose of the step
    order: int  # Intended position (used for ordering; not necessarily contiguous)

    required_molecule_sets: Sequence[Type] = ()  # Providers that must have produced Molecule sets
    produced_molecule_sets: Sequence[Type] = ()  # Providers this step will produce
    required_data_classes: Sequence[Type] = ()  # AbstractMolecularData classes needed as input
    produced_data_classes: Sequence[Type] = ()  # Data classes produced/transformed by this step

    allows_branching: bool = True  # If True, parameter changes can spawn a new branch
    parameters_schema: Dict[str, JSONValue] = {}  # JSON schema-like structure describing accepted parameters

    def prepare(self, step_execution, parameters: Dict[str, JSONValue]):  # pragma: no cover - hook
        return None

    def execute(self, step_execution, parameters: Optional[Dict[str, JSONValue]] = None):  # noqa: D401
        """Template method that wraps concrete ``_process_step`` implementations.

        Subclases sólo necesitan implementar ``_process_step``; este método
        maneja la orquestación y la marca de finalización. Se mantiene
        separado de ``_process_step`` para permitir pruebas unitarias/directas
        del procesamiento puro si es necesario.
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
    def _process_step(self, input_data: JSONDict, step_execution, parameters: Dict[str, JSONValue]):  # noqa: D401
        raise NotImplementedError

    def can_execute(self, execution) -> bool:
        for family in execution.families.all():
            for data_class in self.required_data_classes:
                for _ in family.members.all():
                    method = execution.get_data_retrieval_method(family.family_id, data_class.__name__)
                    if not method:
                        return False
        return True

    def get_progress(self, execution) -> float:
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
