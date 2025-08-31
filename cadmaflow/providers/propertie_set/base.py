"""Base abstracta para lógica de Providers.

Desacopla la lógica Python de los modelos persistentes. Subclases implementan
`execute` y usan helpers para crear/actualizar `ProviderExecution`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from cadmaflow.models.choices import StatusChoices
from cadmaflow.models.providers import DataProvider, ProviderExecution


class ProviderLogic(ABC):
    key: str = ""
    version: str = "1.0"
    description: str = ""
    calculable_properties: list[str] = []
    available_steps: list[str] = []

    def __init__(self, record: DataProvider):
        self.record = record

    @abstractmethod
    def execute(self, **kwargs) -> ProviderExecution:  # pragma: no cover - interface
        raise NotImplementedError

    def _start_execution(self, *, parameters: dict) -> ProviderExecution:
        return ProviderExecution.objects.create(
            provider=self.record,
            calculated_properties=self.calculable_properties,
            execution_parameters=parameters,
            status=StatusChoices.RUNNING,
        )

    def _complete_execution(self, exec_obj: ProviderExecution, *, results: dict, families=None, molecules=None):
        if families:
            exec_obj.families.add(*families)
        if molecules:
            exec_obj.molecules.add(*molecules)
        exec_obj.results = results
        exec_obj.status = StatusChoices.COMPLETED
        exec_obj.save(update_fields=["results", "status", "updated_at"])
        return exec_obj

    def _fail_execution(self, exec_obj: ProviderExecution, *, error: str):  # pragma: no cover - simple path
        exec_obj.results = {"error": error}
        exec_obj.status = StatusChoices.FAILED
        exec_obj.save(update_fields=["results", "status", "updated_at"])
        return exec_obj
