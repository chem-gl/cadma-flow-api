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
	"""
	Clase abstracta base para providers de conjuntos moleculares.

	Responsabilidad:
		- Definir el contrato mínimo para cualquier provider que genere o inyecte
		  moléculas en el sistema.
		- Cada implementación concreta debe definir un identificador único (key),
		  una descripción y el método fetch.

	Contrato de implementación:
		- key: str (obligatorio, único para cada provider)
		- description: str (descripción legible para humanos)
		- params_spec: dict con la especificación de parámetros aceptados (puede ser vacío)
		- fetch: método que retorna un iterable de diccionarios con la estructura de molécula cruda
	"""

	key: str = ""  # Identificador único del provider (snake_case)
	description: str = ""  # Descripción legible para humanos
	params_spec: dict[str, dict[str, JSONValue]] = {}  # Especificación de parámetros aceptados

	def __init_subclass__(cls, **kwargs: object) -> None:
		"""
		Hook de inicialización de subclases.
		Verifica que cada implementación defina un key único.
		"""
		super().__init_subclass__(**kwargs)
		if not cls.key:
			raise ValueError(f"Provider {cls.__name__} debe definir un 'key' no vacío")

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

	@abstractmethod
	def fetch(self, *, params: dict[str, JSONValue]) -> Iterable[dict[str, JSONValue]]:
		"""
		Método abstracto que debe ser implementado por cada provider concreto.
		Debe retornar un iterable de diccionarios, cada uno representando una molécula cruda.
		Cada diccionario debe contener al menos el campo 'inchikey'.
		params: diccionario de parámetros de configuración.
		"""
		raise NotImplementedError("Las subclases deben implementar fetch() retornando moléculas.")

	def validate_params(self, params: dict[str, JSONValue]) -> dict[str, JSONValue]:
		"""
		Validación ligera de parámetros (opcional, puede ser sobreescrito).
		params: diccionario de parámetros a validar.
		Retorna el mismo diccionario si es válido.
		"""
		return params

	def run(self, *, params: dict[str, JSONValue]) -> list[dict[str, JSONValue]]:
		"""
		Punto de entrada público: valida los parámetros y retorna la lista de moléculas.
		params: diccionario de parámetros de configuración.
		"""
		validated = self.validate_params(params)
		return list(self.fetch(params=validated))


# Backward compatible alias (old name used in some early code/docs)
MoleculeSetProvider = MoleculeSetProviderBase

__all__ = ["MoleculeSetProviderBase", "MoleculeSetProvider"]
