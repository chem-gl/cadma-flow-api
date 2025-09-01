"""Abstract base classes for molecular data domain.

This module defines a generic, strongly typed base class that all concrete
"molecular data" records must inherit from. It centralises:

* Strong typing of the native Python value with a TypeVar (``T``)
* JSON serialisation / deserialisation hooks
* Provenance metadata (source program, version, user provided tag)
* Data quality fields (confidence, approval flag)
* A freezing mechanism to make data immutable for workflow reproducibility
* Helper validation utilities

Sub‑classes only need to implement a minimal contract:

* ``get_native_type()`` -> str (one of ``NativeTypeChoices``)
* ``get_value_type()``  -> Python ``type`` used for the native value
* ``serialize_value(value: T) -> str``
* ``deserialize_value(serialized_value: str) -> T``
* Retrieval orchestration hooks ``get_data_retrieval_methods`` & ``retrieve_data``

The base class purposefully avoids making assumptions about how the native
value is stored beyond being represented inside ``value_json``. Concrete
implementations are free to structure their JSON payload so long as they can
reconstruct the native type and satisfy validation.
"""

from __future__ import annotations

import uuid
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, Type, TypeVar, cast

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.base import ModelBase as DjangoModelBase
from django.utils import timezone

from cadmaflow.utils.types import JSONValue

from .choices import NativeTypeChoices, SourceChoices


class _AbstractDataModelBase(ABCMeta, DjangoModelBase):
    """
    Metaclase que combina Django ModelBase y ABCMeta.
    Permite que los modelos definan métodos abstractos sin conflictos de metaclase.
    Es útil para crear modelos abstractos que requieren implementación de métodos en subclases.
    """
    pass

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .models import Molecule  # noqa: F401

User = get_user_model()

# Type variable for native value
T = TypeVar('T')

SUBCLASS_REGISTRY: dict[str, 'Type[AbstractMolecularData[Any]]'] = {}


T_co = TypeVar("T_co", covariant=False)

class AbstractMolecularData(models.Model, Generic[T_co], metaclass=_AbstractDataModelBase):
    """
    Clase abstracta base genérica para todos los datos moleculares.

    Esta clase define el contrato mínimo para cualquier tipo de dato molecular.
    Utiliza tipado fuerte con TypeVar para máxima seguridad y flexibilidad.

    Contrato de implementación para subclases:
        - Definir el tipo nativo de valor (get_native_type, get_value_type)
        - Implementar métodos de serialización/deserialización
        - Implementar métodos de obtención y validación de datos
        - Gestionar metadatos de procedencia, calidad y congelación
    """
    
    data_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """Identificador único universal para este dato molecular."""

    molecule = models.ForeignKey(
        'cadmaflow_models.Molecule', on_delete=models.CASCADE, related_name='%(class)s_entries')
    """Referencia a la molécula a la que pertenece este dato."""

    value_json = models.TextField(
        help_text="Valor serializado como JSON para soportar cualquier tipo de dato")
    """Valor almacenado como texto JSON (permite cualquier tipo de dato)."""

    native_type = models.CharField(
        max_length=20, choices=NativeTypeChoices.choices,
        help_text="Tipo de dato nativo que representa este valor")
    """Tipo de dato nativo (definido por la subclase, ej: FLOAT, STRING, etc.)."""

    source = models.CharField(
        max_length=20, choices=SourceChoices.choices, default=SourceChoices.USER)
    """Origen del dato molecular (ej: USER, TEST, AMBIT, etc.)."""

    source_name = models.CharField(
        max_length=100, help_text="Ej: 'logP-calc'")
    """Nombre lógico del origen del dato (ej: nombre del algoritmo o provider)."""

    source_version = models.CharField(
        max_length=50, blank=True, help_text="Versión del software")
    """Versión del software o método que generó el dato."""

    property_name = models.CharField(
        max_length=100, help_text="Nombre lógico de la propiedad calculada", default="")
    """Nombre lógico de la propiedad (permite agrupar variantes de distintos providers)."""

    provider_execution = models.ForeignKey(
        'cadmaflow_models.ProviderExecution', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_records', help_text="Ejecución del provider que generó este dato")
    """Referencia a la ejecución del provider que generó el dato (si aplica)."""

    user_tag = models.CharField(
        max_length=100, blank=True, help_text="Etiqueta para distinguir diferentes entradas del usuario")
    """Etiqueta para distinguir diferentes entradas del usuario."""

    confidence_score = models.FloatField(
        default=1.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="0-1, 1 = máxima confianza")
    """Puntaje de confianza en el dato (0-1, 1 = máxima confianza)."""

    is_approved = models.BooleanField(default=False)
    """Indica si el dato ha sido aprobado por un revisor o proceso externo."""

    is_frozen = models.BooleanField(default=False, help_text="Si está congelado, no debe modificarse")
    """Indica si el dato está congelado (no debe modificarse para reproducibilidad)."""

    frozen_at = models.DateTimeField(blank=True, null=True)
    """Fecha y hora en que el dato fue congelado."""

    frozen_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='frozen_%(class)s')
    """Usuario que congeló el dato (si aplica)."""

    data_retrieval_config = models.JSONField(
        default=dict, blank=True,
        help_text="Configuración específica para obtener este tipo de dato")
    """Configuración específica para obtener este tipo de dato molecular."""

    created_at = models.DateTimeField(auto_now_add=True)
    """Fecha y hora de creación del dato."""

    updated_at = models.DateTimeField(auto_now=True)
    """Fecha y hora de última actualización del dato."""
    
    class Meta:
        abstract = True  # Indica que esta clase es abstracta y no crea tabla en la BD
        ordering = ['-created_at']  # Ordena por fecha de creación descendente
        indexes = [
            models.Index(fields=['molecule', 'source', 'user_tag']),  # Índice para búsquedas rápidas por molécula, origen y tag
            models.Index(fields=['is_frozen']),  # Índice para filtrar datos congelados
            models.Index(fields=['native_type']),  # Índice por tipo nativo
            models.Index(fields=['molecule', 'property_name']),  # Índice por molécula y propiedad
            models.Index(fields=['property_name', 'provider_execution']),  # Índice por propiedad y ejecución de provider
        ]
    
    @abstractmethod
    def get_native_type(self) -> str:
        """
        Método abstracto que debe ser implementado por subclases.
        Debe devolver el tipo de dato nativo que maneja la clase (ej: FLOAT, STRING).
        """
        pass
    
    @abstractmethod
    def get_value_type(self) -> Type[T_co]:
        """
        Método abstracto que debe ser implementado por subclases.
        Debe devolver el tipo Python nativo que representa el valor (ej: float, str, dict).
        """
        pass
    
    @abstractmethod
    def serialize_value(self, value: T_co) -> str:
        """
        Método abstracto que debe ser implementado por subclases.
        Convierte el valor nativo a formato string para almacenamiento (ej: JSON).
        value: valor en formato nativo a serializar.
        """
        pass
    
    @abstractmethod
    def deserialize_value(self, serialized_value: str) -> T_co:
        """
        Método abstracto que debe ser implementado por subclases.
        Convierte el valor serializado (string) de vuelta a formato nativo.
        serialized_value: valor serializado como string.
        """
        pass
    
    def validate_value_type(self, value: object) -> T_co:
        """
        Valida en tiempo de ejecución que el valor es del tipo esperado.
        Puede ser extendido para validaciones profundas si es necesario.
        value: valor a validar.
        """
        expected = self.get_value_type()
        if not isinstance(value, expected):  # type: ignore[arg-type]
            raise TypeError(f"Se esperaba {expected}, se obtuvo {type(value)}")
        return value
    
    def get_value(self) -> T_co:
        """
        Obtiene el valor en su formato nativo, validando el tipo.
        Retorna el valor convertido al tipo nativo T.
        Lanza ValueError si el valor no puede ser deserializado o validado.
        """
        try:
            native_value = self.deserialize_value(self.value_json)
            return self.validate_value_type(native_value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Error al obtener valor: {e}") from e
    
    def set_value(self, value: T_co) -> None:
        """
        Establece el valor, validando el tipo y serializándolo para almacenamiento.
        value: valor a almacenar en formato nativo.
        Lanza ValueError si el valor no es del tipo esperado.
        Lanza RuntimeError si el dato está congelado.
        """
        if self.is_frozen:
            raise RuntimeError("No se puede modificar un dato congelado")
        try:
            validated_value = self.validate_value_type(value)
            serialized = self.serialize_value(validated_value)
            self.value_json = serialized  # serialize_value debe devolver str JSON
            self.native_type = self.get_native_type()
        except (TypeError, ValueError) as e:
            raise ValueError(f"Error al establecer valor: {e}") from e
    
    def freeze(self, user: Any | None = None) -> None:
        """
        Congela el dato para evitar modificaciones futuras.
        user: usuario que realiza la congelación.
        """
        self.is_frozen = True
        self.frozen_at = timezone.now()
        # Aceptamos None o instancia de User; cast para satisfacer mypy sobre ForeignKey opcional.
        self.frozen_by = cast(Any, user)
        self.save(update_fields=["is_frozen", "frozen_at", "frozen_by", "updated_at"])
        
    @classmethod
    @abstractmethod
    def get_data_retrieval_methods(cls) -> Dict[str, Dict[str, JSONValue]]:
        """
        Método abstracto que debe ser implementado por subclases.
        Debe devolver un diccionario con los métodos disponibles para obtener este tipo de dato.
        """
        pass
    
    @classmethod
    @abstractmethod
    def retrieve_data(
        cls,
        molecule: 'Molecule',
        method: str,
        config: Optional[Dict[str, JSONValue]] = None,
        user_tag: Optional[str] = None,
    ) -> 'AbstractMolecularData[Any]':
        """
        Método abstracto que debe ser implementado por subclases.
        Obtiene el dato usando el método especificado y la configuración dada.
        molecule: instancia de Molecule para la que se obtiene el dato.
        method: nombre del método de obtención.
        config: configuración adicional para el método.
        user_tag: etiqueta opcional para datos de usuario.
        """
        pass
    
    def __str__(self) -> str:
        """
        Representación legible del dato molecular, útil para debugging y administración.
        Incluye información de la molécula, clase, propiedad, tag y estado de congelación.
        """
        tag_info = f" [{self.user_tag}]" if self.user_tag else ""
        frozen_info = " ❄️" if self.is_frozen else ""
        prop_info = f" · {self.property_name}" if self.property_name else ""
        try:
            value_repr = str(self.get_value())[:80]
            if len(value_repr) == 80:
                value_repr += '…'
        except Exception as e:
            value_repr = f"Error: {e}"
        return f"{self.molecule.inchikey} • {self.__class__.__name__}{prop_info}{tag_info}{frozen_info}: {value_repr}"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Registro automático de subclases concretas para facilitar la resolución dinámica.
        No registra clases abstractas.
        """
        super().__init_subclass__(**kwargs)
        if getattr(getattr(cls, '_meta', None), 'abstract', False):
            return
        SUBCLASS_REGISTRY[cls.__name__] = cls


def get_data_class_by_name(name: str) -> Type[AbstractMolecularData[Any]] | None:
    """
    Devuelve la clase de dato molecular registrada bajo el nombre dado.
    name: nombre de la clase buscada.
    """
    return SUBCLASS_REGISTRY.get(name)