"""Base abstractions for molecular property providers.

Estos providers calculan u obtienen propiedades (QSAR, físicas, etc.) para
moléculas individuales. No crean moléculas; operan sobre una ya existente.

Contrato típico:
	class LogPProvider(PropertyProviderBase):
		key = "logp_calc"
		provides = ["logP"]  # nombres lógicos de propiedades

		def compute(self, *, molecule: Molecule, params: dict):
			value = self._external_tool(molecule.smiles, params)
			return {"property": "logP", "value": value, "native_type": "FLOAT"}

La salida de `compute` es una lista o iterable de dicts con esquema mínimo:
	{
		"property": str,          # nombre lógico
		"value": JSONValue,       # valor nativo serializable
		"native_type": str,       # coincide con NativeTypeChoices
		"extra": { ... }          # opcional metadata adicional
	}
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from cadmaflow.utils.types import JSONValue


class PropertyProviderBase(ABC):
	"""Abstract base for per-molecule property providers."""

	key: str = ""
	provides: list[str] = []  # logical property names produced
	description: str = ""
	params_spec: dict[str, dict[str, JSONValue]] = {}

	def __init_subclass__(cls, **kwargs):  # noqa: D401
		super().__init_subclass__(**kwargs)
		if not cls.key:
			raise ValueError(f"Property provider {cls.__name__} must define 'key'")
		if not cls.provides:
			raise ValueError(f"Property provider {cls.__name__} must define non-empty 'provides' list")

	@classmethod
	def get_key(cls) -> str:
		return cls.key

	@classmethod
	def get_spec(cls) -> dict[str, dict[str, JSONValue]]:
		return cls.params_spec

	@classmethod
	def get_provides(cls) -> list[str]:
		return cls.provides

	def validate_params(self, params: dict[str, JSONValue]) -> dict[str, JSONValue]:  # pragma: no cover
		return params

	@abstractmethod
	def compute(self, *, molecule, params: dict[str, JSONValue]) -> Iterable[dict[str, JSONValue]]:
		"""Yield property result dicts (see module docstring)."""
		raise NotImplementedError

	def run(self, *, molecule, params: dict[str, JSONValue]) -> list[dict[str, JSONValue]]:
		validated = self.validate_params(params)
		return list(self.compute(molecule=molecule, params=validated))

# Backward compatible alias
PropertySetProvider = PropertyProviderBase

__all__ = ["PropertyProviderBase", "PropertySetProvider"]
