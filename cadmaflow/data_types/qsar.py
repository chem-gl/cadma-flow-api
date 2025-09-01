"""Modelos concretos para propiedades QSAR.

Este módulo implementa 4 propiedades básicas de screening. Cada clase deriva de
``AbstractMolecularData`` (vía import diferido) y define:
 - PROPERTY_NAME lógico
 - Tipos nativos / serialización JSON simple
 - Métodos de *retrieval* mínimos (``user_input`` como ejemplo)

Los métodos de obtención son deliberadamente simples; en un futuro se pueden
añadir providers específicos (ej: cálculos externos) agregando nuevas claves en
``get_data_retrieval_methods``.
"""

from __future__ import annotations

import json
from typing import Dict, Optional, Type

from cadmaflow.models.abstract_models import AbstractMolecularData
from cadmaflow.models.choices import NativeTypeChoices, SourceChoices
from cadmaflow.utils.types import JSONValue


class _BaseSimpleFloatData(AbstractMolecularData[float]):
    class Meta(AbstractMolecularData.Meta):
        abstract = True

    def get_native_type(self) -> str:  # type: ignore[override]
        return NativeTypeChoices.FLOAT

    def get_value_type(self) -> Type[float]:  # type: ignore[override]
        return float

    def serialize_value(self, value: float) -> str:  # type: ignore[override]
        return json.dumps(value)

    def deserialize_value(self, serialized_value: str) -> float:  # type: ignore[override]
        return float(json.loads(serialized_value))

    @classmethod
    def get_data_retrieval_methods(cls) -> Dict[str, Dict[str, JSONValue]]:  # type: ignore[override]
        return {
            "user_input": {
                "description": "Valor proporcionado por el usuario",
                "config_schema": {"value": {"type": "number"}},
            }
        }

    @classmethod
    def retrieve_data(cls, molecule, method: str, config: Optional[Dict[str, JSONValue]] = None,
                      user_tag: Optional[str] = None):  # type: ignore[override]
        methods = cls.get_data_retrieval_methods()
        if method not in methods:
            raise ValueError(f"Método {method} no soportado para {cls.__name__}")
        cfg = config or {}
        if method == "user_input":
            if "value" not in cfg:
                raise ValueError("Se requiere 'value' en config para user_input")
            obj = cls(
                molecule=molecule,
                value_json=json.dumps(float(cfg["value"]) if isinstance(cfg["value"], (int, float, str)) else float("nan")),
                native_type=NativeTypeChoices.FLOAT,
                source=SourceChoices.USER,
                source_name="user-input",
                property_name=getattr(cls, "PROPERTY_NAME", cls.__name__.lower()),
                user_tag=user_tag or "default",
            )
            obj.save()
            return obj
        raise NotImplementedError(method)


class _BaseSimpleStringData(AbstractMolecularData[str]):
    class Meta(AbstractMolecularData.Meta):
        abstract = True

    def get_native_type(self) -> str:  # type: ignore[override]
        return NativeTypeChoices.STRING

    def get_value_type(self) -> Type[str]:  # type: ignore[override]
        return str

    def serialize_value(self, value: str) -> str:  # type: ignore[override]
        return json.dumps(value)

    def deserialize_value(self, serialized_value: str) -> str:  # type: ignore[override]
        return str(json.loads(serialized_value))

    @classmethod
    def get_data_retrieval_methods(cls) -> Dict[str, Dict[str, JSONValue]]:  # type: ignore[override]
        return {
            "user_input": {
                "description": "Valor proporcionado por el usuario",
                "config_schema": {"value": {"type": "string"}},
            }
        }

    @classmethod
    def retrieve_data(cls, molecule, method: str, config: Optional[Dict[str, JSONValue]] = None,
                      user_tag: Optional[str] = None):  # type: ignore[override]
        methods = cls.get_data_retrieval_methods()
        if method not in methods:
            raise ValueError(f"Método {method} no soportado para {cls.__name__}")
        cfg = config or {}
        if method == "user_input":
            if "value" not in cfg:
                raise ValueError("Se requiere 'value' en config para user_input")
            obj = cls(
                molecule=molecule,
                value_json=json.dumps(str(cfg["value"])),
                native_type=NativeTypeChoices.STRING,
                source=SourceChoices.USER,
                source_name="user-input",
                property_name=getattr(cls, "PROPERTY_NAME", cls.__name__.lower()),
                user_tag=user_tag or "default",
            )
            obj.save()
            return obj
        raise NotImplementedError(method)


class LogPData(_BaseSimpleFloatData):
    """
    Clase concreta para el coeficiente de partición LogP (octanol/agua).

    Uso típico:
        - Se utiliza para almacenar el valor de LogP calculado o proporcionado por el usuario.
        - El método de obtención principal es 'user_input', que espera un diccionario {'value': float}.
        - Permite la serialización/deserialización automática y validación de tipo.
    Ejemplo de creación:
        LogPData.retrieve_data(molecule, method="user_input", config={"value": 2.5})
    """
    PROPERTY_NAME = "logp"  # Nombre lógico de la propiedad
    class Meta(_BaseSimpleFloatData.Meta):
        app_label = 'cadmaflow_models'


class ToxicityData(_BaseSimpleStringData):
    """
    Clase concreta para la clasificación de toxicidad (etiqueta string).

    Uso típico:
        - Permite almacenar una etiqueta de toxicidad (ej: "Tóxico", "No tóxico") para una molécula.
        - El método de obtención principal es 'user_input', que espera un diccionario {'value': str}.
        - Facilita la validación y serialización automática.
    Ejemplo de creación:
        ToxicityData.retrieve_data(molecule, method="user_input", config={"value": "Tóxico"})
    """
    PROPERTY_NAME = "toxicity"  # Nombre lógico de la propiedad
    class Meta(_BaseSimpleStringData.Meta):
        app_label = 'cadmaflow_models'


class AbsorptionData(_BaseSimpleStringData):
    """
    Clase concreta para la clasificación cualitativa de absorción (string).

    Uso típico:
        - Permite almacenar una etiqueta de absorción (ej: "Alta", "Baja") para una molécula.
        - El método de obtención principal es 'user_input', que espera un diccionario {'value': str}.
        - Facilita la validación y serialización automática.
    Ejemplo de creación:
        AbsorptionData.retrieve_data(molecule, method="user_input", config={"value": "Alta"})
    """
    PROPERTY_NAME = "absorption"  # Nombre lógico de la propiedad
    class Meta(_BaseSimpleStringData.Meta):
        app_label = 'cadmaflow_models'


class MutagenicityData(_BaseSimpleStringData):
    """
    Clase concreta para la clasificación cualitativa de mutagenicidad (string).

    Uso típico:
        - Permite almacenar una etiqueta de mutagenicidad (ej: "Mutagénico", "No mutagénico") para una molécula.
        - El método de obtención principal es 'user_input', que espera un diccionario {'value': str}.
        - Facilita la validación y serialización automática.
    Ejemplo de creación:
        MutagenicityData.retrieve_data(molecule, method="user_input", config={"value": "Mutagénico"})
    """
    PROPERTY_NAME = "mutagenicity"  # Nombre lógico de la propiedad
    class Meta(_BaseSimpleStringData.Meta):
        app_label = 'cadmaflow_models'