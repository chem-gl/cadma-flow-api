"""Modelos concretos para propiedades QSAR ingresadas por el usuario.

Incluye propiedades básicas típicas de un screening ADMET/QSAR inicial:
 - logP (float)
 - toxicidad (categoría libre)
 - absorción (categoría libre)
 - mutagenicidad (categoría libre / resultado ensayos Ames, etc.)

Cada clase es un contenedor especializado que facilita:
 - Tipado fuerte del valor nativo
 - Registro de la propiedad (``property_name``)
 - Producción a través de providers (``provider_execution``)
 - Posibles variantes futuras (diferentes fuentes)
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional, Type

from .abstract_models import AbstractMolecularData
from .choices import NativeTypeChoices, SourceChoices
from .models import Molecule  # type: ignore


class _BaseSimpleData(AbstractMolecularData[Any]):  # tipo interno base flexible
    class Meta:
        abstract = True

    @classmethod
    def get_data_retrieval_methods(cls) -> Dict[str, Dict[str, Any]]:  # pragma: no cover - trivial mapping
        return {
            "user_input": {
                "description": "Valor ingresado manualmente por el usuario",
                "requires": ["value"],
            }
        }

    @classmethod
    def retrieve_data(
        cls,
        molecule: Molecule,
        method: str,
        config: Optional[Dict[str, Any]] = None,
        user_tag: Optional[str] = None,
    ) -> "_BaseSimpleData":  # type: ignore[override]
        if method != "user_input":  # pragma: no cover - validación simple
            raise ValueError(f"Método no soportado: {method}")
        if not config or "value" not in config:
            raise ValueError("config debe incluir 'value'")
        inst = cls(
            molecule=molecule,
            native_type=cls.get_native_type(),
            source=SourceChoices.USER,
            source_name="user-input",
            source_version="1.0",
            property_name=getattr(cls, "PROPERTY_NAME", ""),
            user_tag=user_tag or "",
        )
        inst.set_value(config["value"])  # valida y serializa
        inst.save()
        return inst


class LogPData(_BaseSimpleData):
    PROPERTY_NAME = "logp"

    def get_native_type(self) -> str:  # type: ignore[override]
        return NativeTypeChoices.FLOAT

    def get_value_type(self) -> Type[float]:  # type: ignore[override]
        return float

    def serialize_value(self, value: float) -> str:  # type: ignore[override]
        return json.dumps(value)

    def deserialize_value(self, serialized_value: str) -> float:  # type: ignore[override]
        return float(json.loads(serialized_value))


class ToxicityData(_BaseSimpleData):
    PROPERTY_NAME = "toxicity"

    def get_native_type(self) -> str:  # type: ignore[override]
        return NativeTypeChoices.STRING

    def get_value_type(self) -> Type[str]:  # type: ignore[override]
        return str

    def serialize_value(self, value: str) -> str:  # type: ignore[override]
        return json.dumps(value)

    def deserialize_value(self, serialized_value: str) -> str:  # type: ignore[override]
        return str(json.loads(serialized_value))


class AbsorptionData(_BaseSimpleData):
    PROPERTY_NAME = "absorption"

    def get_native_type(self) -> str:  # type: ignore[override]
        return NativeTypeChoices.STRING

    def get_value_type(self) -> Type[str]:  # type: ignore[override]
        return str

    def serialize_value(self, value: str) -> str:  # type: ignore[override]
        return json.dumps(value)

    def deserialize_value(self, serialized_value: str) -> str:  # type: ignore[override]
        return str(json.loads(serialized_value))


class MutagenicityData(_BaseSimpleData):
    PROPERTY_NAME = "mutagenicity"

    def get_native_type(self) -> str:  # type: ignore[override]
        return NativeTypeChoices.STRING

    def get_value_type(self) -> Type[str]:  # type: ignore[override]
        return str

    def serialize_value(self, value: str) -> str:  # type: ignore[override]
        return json.dumps(value)

    def deserialize_value(self, serialized_value: str) -> str:  # type: ignore[override]
        return str(json.loads(serialized_value))
