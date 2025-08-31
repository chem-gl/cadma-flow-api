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
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.base import ModelBase as DjangoModelBase
from django.utils import timezone

from .choices import NativeTypeChoices, SourceChoices


class _AbstractDataModelBase(ABCMeta, DjangoModelBase): 
    """Metaclass that combines Django's ``ModelBase`` with ``ABCMeta``.

    This allows the model to define ``@abstractmethod`` methods without
    triggering the classic *metaclass conflict* error.
    """
    pass

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .models import Molecule  # noqa: F401

User = get_user_model()

# Type variable for native value
T = TypeVar('T')

SUBCLASS_REGISTRY: dict[str, Type['AbstractMolecularData']] = {}


class AbstractMolecularData(models.Model, metaclass=_AbstractDataModelBase):
    """
    CLASE ABSTRACTA BASE GENÉRICA para todos los datos moleculares.
    
    Utiliza TypeVar para una tipificación fuerte y flexible.
    
    Propósito:
    - Proporcionar una estructura común para todos los tipos de datos moleculares
    - Implementar sistema de tipos fuertes con TypeVar
    - Permitir que cada subclase defina claramente su tipo de valor nativo
    - Gestionar metadatos de procedencia y calidad de datos
    - Implementar el patrón de congelación de datos
    
    Características clave:
    - Sistema de tipos genéricos con TypeVar para máxima flexibilidad y seguridad
    - Serialización/deserialización automática con verificación de tipos
    - Cada subclase define claramente su tipo de valor nativo (T)
    - Soporte para tipos complejos con validación
    """
    
    # Identificador único universal para este dato
    data_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación con la molécula a la que pertenece este dato
    molecule = models.ForeignKey('Molecule', on_delete=models.CASCADE, 
                               related_name='%(class)s_entries')
    
    # Valor almacenado como texto JSON (permite cualquier tipo de dato)
    value_json = models.TextField(
        help_text="Valor serializado como JSON para soportar cualquier tipo de dato"
    )
    
    # Tipo de dato nativo (definido por la subclase)
    native_type = models.CharField(
        max_length=20, 
        choices=NativeTypeChoices.choices,
        help_text="Tipo de dato nativo que representa este valor"
    )
    
    # Metadatos de origen del dato
    source = models.CharField(max_length=20, choices=SourceChoices.choices, 
                            default=SourceChoices.USER)
    source_name = models.CharField(max_length=100, help_text="Ej: 'logP-calc'")
    source_version = models.CharField(max_length=50, blank=True, 
                                    help_text="Versión del software")

    # Nombre lógico de la propiedad (permite agrupar variantes de distintos providers)
    property_name = models.CharField(max_length=100, help_text="Nombre lógico de la propiedad calculada", default="")

    # Ejecución del provider que generó el dato (si aplica)
    provider_execution = models.ForeignKey(
        'cadmaflow_models.ProviderExecution',  # referencia explícita app_label.modelo
        on_delete=models.SET_NULL, null=True, blank=True,
        # Usamos patrón con placeholder para evitar colisiones entre subclases concretas
        # (cada modelo concreto obtendrá su propio reverse accessor en ProviderExecution):
        #   provider_execution.<NombreModeloEnMinusculas>_records.all()
        related_name='%(class)s_records',
        help_text="Ejecución del provider que generó este dato"
    )
    
    # Etiqueta para distinguir diferentes entradas del usuario
    user_tag = models.CharField(max_length=100, blank=True,
                              help_text="Etiqueta para distinguir diferentes entradas del usuario")
    
    # Sistema de control de calidad
    confidence_score = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="0-1, 1 = máxima confianza"
    )
    is_approved = models.BooleanField(default=False)
    
    # Sistema de congelación de datos
    is_frozen = models.BooleanField(default=False, 
                                  help_text="Si está congelado, no debe modificarse")
    frozen_at = models.DateTimeField(blank=True, null=True)
    frozen_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='frozen_%(class)s')
    
    # Configuración específica para obtener este tipo de dato
    data_retrieval_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuración específica para obtener este tipo de dato"
    )
    
    # Timestamps de auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['molecule', 'source', 'user_tag']),
            models.Index(fields=['is_frozen']),
            models.Index(fields=['native_type']),
            models.Index(fields=['molecule', 'property_name']),
            models.Index(fields=['property_name', 'provider_execution']),
        ]
    
    @abstractmethod
    def get_native_type(self) -> str:
        """
        DEBE SER IMPLEMENTADO POR SUBCLASES:
        Devuelve el tipo de dato nativo que maneja esta clase.
        
        Returns:
            String que identifica el tipo de dato (de NativeTypeChoices)
        """
        pass
    
    @abstractmethod
    def get_value_type(self) -> Type[Any]:
        """
        DEBE SER IMPLEMENTADO POR SUBCLASES:
        Devuelve el tipo Python nativo que representa el valor.
        
        Returns:
            Tipo Python (ej: float, bool, List[Dict], etc.)
        """
        pass
    
    @abstractmethod
    def serialize_value(self, value: Any) -> str:
        """
        DEBE SER IMPLEMENTADO POR SUBCLASES:
        Convierte el valor nativo a formato string para almacenamiento.
        
        Args:
            value: Valor en formato nativo a serializar
            
        Returns:
            String que representa el valor serializado
        """
        pass
    
    @abstractmethod
    def deserialize_value(self, serialized_value: str) -> Any:
        """
        DEBE SER IMPLEMENTADO POR SUBCLASES:
        Convierte el valor serializado de vuelta a formato nativo.
        
        Args:
            serialized_value: Valor serializado como string
            
        Returns:
            Valor en formato nativo (tipo T)
        
        Raises:
            ValueError: Si el valor no puede ser deserializado al tipo esperado
        """
        pass
    
    def validate_value_type(self, value: Any) -> Any:
        """Basic runtime type validation; deep element checks intentionally omitted.

        (Se puede extender con validación profunda si es necesario.)
        """
        expected = self.get_value_type()
        if not isinstance(value, expected):  # type: ignore[arg-type]
            raise TypeError(f"Se esperaba {expected}, se obtuvo {type(value)}")
        return value
    
    def get_value(self) -> Any:
        """
        Obtiene el valor en su formato nativo con validación de tipo.
        
        Returns:
            Valor convertido al tipo nativo T
            
        Raises:
            ValueError: Si el valor no puede ser deserializado o validado
        """
        try:
            native_value = self.deserialize_value(self.value_json)
            return self.validate_value_type(native_value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Error al obtener valor: {e}") from e
    
    def set_value(self, value: Any) -> None:
        """
        Establece el valor, validando el tipo y serializándolo para almacenamiento.
        
        Args:
            value: Valor a almacenar en formato nativo
            
        Raises:
            ValueError: Si el valor no es del tipo esperado
            RuntimeError: Si el dato está congelado
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
    
    def freeze(self, user) -> None:
        """Congela el dato para evitar modificaciones."""
        self.is_frozen = True
        self.frozen_at = timezone.now()
        self.frozen_by = user
        self.save(update_fields=["is_frozen", "frozen_at", "frozen_by", "updated_at"])
    
    @classmethod
    @abstractmethod
    def get_data_retrieval_methods(cls) -> Dict[str, Dict[str, Any]]:
        """
        Devuelve los métodos disponibles para obtener este tipo de dato.
        
        Returns:
            Diccionario con métodos de obtención y sus configuraciones
        """
        pass
    
    @classmethod
    @abstractmethod
    def retrieve_data(cls, molecule: 'Molecule', method: str, 
                      config: Optional[Dict[str, Any]] = None,
                      user_tag: Optional[str] = None) -> 'AbstractMolecularData':
        """
        Obtiene el dato usando el método especificado.
        
        Args:
            molecule: Molécula para la que se obtendrá el dato
            method: Nombre del método de obtención
            config: Configuración adicional para el método
            user_tag: Etiqueta opcional para datos de usuario
        
        Returns:
            Instancia del dato obtenido
        """
        pass
    
    def __str__(self) -> str:
        tag_info = f" [{self.user_tag}]" if self.user_tag else ""
        frozen_info = " ❄️" if self.is_frozen else ""
        prop_info = f" · {self.property_name}" if self.property_name else ""
        try:
            value_repr = str(self.get_value())[:80]
            if len(value_repr) == 80:
                value_repr += '…'
        except Exception as e:  # noqa: BLE001
            value_repr = f"Error: {e}"
        return f"{self.molecule.inchikey} • {self.__class__.__name__}{prop_info}{tag_info}{frozen_info}: {value_repr}"

    # Registro automático de subclases
    def __init_subclass__(cls, **kwargs):  # type: ignore[override]
        super().__init_subclass__(**kwargs)
        if getattr(getattr(cls, '_meta', None), 'abstract', False):  # no registrar abstractas
            return
        SUBCLASS_REGISTRY[cls.__name__] = cls


def get_data_class_by_name(name: str) -> Type[AbstractMolecularData] | None:
    return SUBCLASS_REGISTRY.get(name)