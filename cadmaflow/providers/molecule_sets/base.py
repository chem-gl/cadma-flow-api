"""Base abstractions for molecule set providers.

Responsabilidad:
	Definir la interfaz mínima para proveedores que generan/inyectan
	conjuntos de moléculas (familias) dentro de un workflow.

Contrato (para implementadores concretos):
	class MyProvider(MoleculeSetProviderBase):
		key = "my_provider"
		description = "Genera moléculas a partir de ..."

		def fetch(self, *, params: dict) -> list[dict]:
			return [{"inchikey": "...", "name": "...", ...}, ...]

	Donde cada dict debe contener al menos 'inchikey'. Campos extra se
	preservan y pueden ser utilizados por lógica downstream.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from cadmaflow.utils.types import JSONValue


class MoleculeSetProviderBase(ABC):
	"""Abstract base for molecule set providers.

	A provider yields molecular descriptors (dicts) that will later be
	materialized as `Molecule` and optionally grouped into `MolecularFamily`.
	"""

	# Unique identifier (snake_case) used in configs & persistence
	key: str = ""
	# Short human readable description
	description: str = ""

	#: Declarative schema-ish description of expected params (optional)
	#: Example: {"min_logp": {"type": "number", "default": 0.0}}
	params_spec: dict[str, dict[str, JSONValue]] = {}

	def __init_subclass__(cls, **kwargs):  # noqa: D401 - internal registry hook
		super().__init_subclass__(**kwargs)
		if not cls.key:
			raise ValueError(f"Provider {cls.__name__} must define a non-empty 'key'")

	@classmethod
	def get_key(cls) -> str:
		return cls.key

	@classmethod
	def get_spec(cls) -> dict[str, dict[str, JSONValue]]:
		return cls.params_spec

	@abstractmethod
	def fetch(self, *, params: dict[str, JSONValue]) -> Iterable[dict[str, JSONValue]]:
		"""Return an iterable of molecule dicts.

		Each dict MUST include at least 'inchikey'. Additional keys are free
		form (e.g. name, smiles, formula...).
		"""
		raise NotImplementedError

	def validate_params(self, params: dict[str, JSONValue]) -> dict[str, JSONValue]:  # pragma: no cover
		"""Optional light validation; override for custom rules."""
		return params

	def run(self, *, params: dict[str, JSONValue]) -> list[dict[str, JSONValue]]:
		"""Public entrypoint: validate then fetch and normalize to list."""
		validated = self.validate_params(params)
		return list(self.fetch(params=validated))


# Backward compatible alias (old name used in some early code/docs)
MoleculeSetProvider = MoleculeSetProviderBase

__all__ = ["MoleculeSetProviderBase", "MoleculeSetProvider"]
