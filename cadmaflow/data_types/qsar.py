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
from typing import Any, Dict, Optional, Type

from cadmaflow.models.abstract_models import AbstractMolecularData
from cadmaflow.models.choices import NativeTypeChoices, SourceChoices


class _BaseSimpleFloatData(AbstractMolecularData):
    class Meta:
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
    def get_data_retrieval_methods(cls) -> Dict[str, Dict[str, Any]]:  # type: ignore[override]
        return {
            "user_input": {
                "description": "Valor proporcionado por el usuario",
                "config_schema": {"value": {"type": "number"}},
            }
        }

    @classmethod
    def retrieve_data(cls, molecule, method: str, *, config: Optional[Dict[str, Any]] = None,
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
                value_json=json.dumps(float(cfg["value"])),
                native_type=NativeTypeChoices.FLOAT,
                source=SourceChoices.USER,
                source_name="user-input",
                property_name=getattr(cls, "PROPERTY_NAME", cls.__name__.lower()),
                user_tag=user_tag or "default",
            )
            obj.save()
            return obj
        raise NotImplementedError(method)


class _BaseSimpleStringData(AbstractMolecularData):
    class Meta:
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
    def get_data_retrieval_methods(cls) -> Dict[str, Dict[str, Any]]:  # type: ignore[override]
        return {
            "user_input": {
                "description": "Valor proporcionado por el usuario",
                "config_schema": {"value": {"type": "string"}},
            }
        }

    @classmethod
    def retrieve_data(cls, molecule, method: str, *, config: Optional[Dict[str, Any]] = None,
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
    """LogP partition coefficient (octanol/water) simple float value.

    Retrieval methods currently: user_input (expects {'value': float}).
    """
    PROPERTY_NAME = "logp"
    class Meta:
        app_label = 'cadmaflow_models'


class ToxicityData(_BaseSimpleStringData):
    """Toxicity classification / label (string)."""
    PROPERTY_NAME = "toxicity"
    class Meta:
        app_label = 'cadmaflow_models'


class AbsorptionData(_BaseSimpleStringData):
    """Absorption qualitative classification (string)."""
    PROPERTY_NAME = "absorption"
    class Meta:
        app_label = 'cadmaflow_models'


class MutagenicityData(_BaseSimpleStringData):
    """Mutagenicity qualitative classification (string)."""
    PROPERTY_NAME = "mutagenicity"
    class Meta:
        app_label = 'cadmaflow_models'

