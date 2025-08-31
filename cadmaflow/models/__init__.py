"""Dominio: interfaz pública de modelos (lazy import).

Se evita cargar submódulos de modelos durante el arranque de Django para
prevenir ``AppRegistryNotReady`` en escenarios de import temprano (pytest).
Las clases se resuelven bajo demanda mediante ``__getattr__``.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

_EXPORT_MAP: Dict[str, str] = {
	"Molecule": "cadmaflow.models.molecule",
	"MolecularFamily": "cadmaflow.models.molecule",
	"Workflow": "cadmaflow.models.workflow",
	"WorkflowBranch": "cadmaflow.models.workflow",
	"WorkflowExecution": "cadmaflow.models.execution",
	"StepExecution": "cadmaflow.models.step_execution",
	"WorkflowEvent": "cadmaflow.models.events",
	"DataSelection": "cadmaflow.models.selection",
	"ProviderExecution": "cadmaflow.models.providers",
}

__all__ = list(_EXPORT_MAP.keys())

def __getattr__(name: str) -> Any:  # pragma: no cover - resolución dinámica
	if name in _EXPORT_MAP:
		module = import_module(_EXPORT_MAP[name])
		return getattr(module, name)
	raise AttributeError(name)


