"""Implementación concreta de provider de propiedades moleculares.

Incluye comentarios exhaustivos en español para cada variable y método.
"""
from typing import Iterable, TypedDict

from cadmaflow.models.choices import NativeTypeChoices
from cadmaflow.models.molecule import Molecule
from cadmaflow.utils.types import JSONValue

from .base import PropertyProviderBase


class PropertyResultDict(TypedDict):
    """
    Estructura de un resultado de propiedad calculada.
    property: Nombre lógico de la propiedad (string).
    value: Valor calculado (float).
    native_type: Tipo nativo (ej: FLOAT, string).
    extra: Diccionario de metadatos adicionales.
    """
    property: str
    value: float
    native_type: str
    extra: dict

class LogPCalcProvider(PropertyProviderBase):
    """
    Provider que calcula logP para una molécula (simulado).
    key: Identificador único del provider.
    provides: Lista de propiedades que produce este provider.
    description: Descripción legible para humanos.
    params_spec: Especificación de parámetros esperados (vacío en este caso).
    """
    key: str = "logp_calc"
    provides: list[str] = ["logP"]
    description: str = "Calcula logP (coeficiente de partición octanol/agua) de una molécula."
    params_spec: dict[str, dict[str, JSONValue]] = {}

    def compute(self, *, molecule: Molecule, params: dict[str, JSONValue]) -> Iterable[dict[str, JSONValue]]:  # type: ignore[override]
        """
        Simula el cálculo de logP para una molécula dada.
        molecule: instancia de Molecule sobre la que se calcula la propiedad.
        params: parámetros de configuración (no usados en este ejemplo).
        Retorna una lista con un solo resultado de tipo dict[str, JSONValue].
        """
        # Valor simulado de logP (en un caso real, se llamaría a un predictor externo)
        logp_value: float = 2.5  # Valor fijo para ejemplo
        return [{
            "property": "logP",
            "value": logp_value,
            "native_type": NativeTypeChoices.FLOAT,
            "extra": {"comentario": "Valor simulado para pruebas"}
        }]
