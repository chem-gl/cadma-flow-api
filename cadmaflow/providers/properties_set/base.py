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
from typing import Iterable, Protocol, runtime_checkable

from cadmaflow.utils.types import JSONValue


@runtime_checkable
class _MoleculeProto(Protocol):
	smiles: str
	inchi: str
	inchikey: str


class PropertyProviderBase(ABC):
	"""
	Clase abstracta base para providers de propiedades moleculares.

	Responsabilidad:
		- Definir el contrato mínimo para cualquier provider que calcule u obtenga
		  propiedades moleculares (QSAR, físicas, etc.) para una molécula dada.
		- Cada implementación concreta debe definir un identificador único (key),
		  una lista de propiedades que produce (provides), una descripción y el método compute.

	Contrato de implementación:
		- key: str (obligatorio, único para cada provider)
		- provides: list[str] (obligatorio, nombres lógicos de propiedades)
		- description: str (descripción legible para humanos)
		- params_spec: dict con la especificación de parámetros aceptados (puede ser vacío)
		- compute: método que retorna un iterable de diccionarios con el resultado de la propiedad
	"""

	key: str = ""  # Identificador único del provider
	provides: list[str] = []  # Lista de nombres lógicos de propiedades producidas
	description: str = ""  # Descripción legible para humanos
	params_spec: dict[str, dict[str, JSONValue]] = {}  # Especificación de parámetros aceptados

	def __init_subclass__(cls, **kwargs: object) -> None:
		"""
		Hook de inicialización de subclases.
		Verifica que cada implementación defina un key único y una lista provides no vacía.
		"""
		super().__init_subclass__(**kwargs)
		if not cls.key:
			raise ValueError(f"Property provider {cls.__name__} debe definir 'key'")
		if not cls.provides:
			raise ValueError(f"Property provider {cls.__name__} debe definir una lista 'provides' no vacía")

	@classmethod
	def get_key(cls) -> str:
		"""
		Devuelve el identificador único del provider.
		"""
		return cls.key

	@classmethod
	def get_spec(cls) -> dict[str, dict[str, JSONValue]]:
		"""
		Devuelve la especificación de parámetros aceptados por el provider.
		"""
		return cls.params_spec

	@classmethod
	def get_provides(cls) -> list[str]:
		"""
		Devuelve la lista de nombres lógicos de propiedades producidas por el provider.
		"""
		return cls.provides

	def validate_params(self, params: dict[str, JSONValue]) -> dict[str, JSONValue]:
		"""
		Validación ligera de parámetros (opcional, puede ser sobreescrito).
		params: diccionario de parámetros a validar.
		Retorna el mismo diccionario si es válido.
		"""
		return params

	@abstractmethod
	def compute(self, *, molecule: _MoleculeProto, params: dict[str, JSONValue]) -> Iterable[dict[str, JSONValue]]:
		"""
		Método abstracto que debe ser implementado por cada provider concreto.
		Debe retornar un iterable de diccionarios, cada uno representando el resultado de una propiedad.
		molecule: instancia de Molecule sobre la que se calcula la propiedad.
		params: diccionario de parámetros de configuración.
		"""
		raise NotImplementedError("Las subclases deben implementar compute() retornando resultados de propiedad.")

	def run(self, *, molecule: _MoleculeProto, params: dict[str, JSONValue]) -> list[dict[str, JSONValue]]:
		"""
		Punto de entrada público: valida los parámetros y retorna la lista de resultados de propiedad.
		molecule: instancia de Molecule sobre la que se calcula la propiedad.
		params: diccionario de parámetros de configuración.
		"""
		validated = self.validate_params(params)
		return list(self.compute(molecule=molecule, params=validated))

# Backward compatible alias
PropertySetProvider = PropertyProviderBase

__all__ = ["PropertyProviderBase", "PropertySetProvider"]
