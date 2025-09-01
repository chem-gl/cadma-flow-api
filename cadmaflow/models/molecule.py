"""Molecule and MolecularFamily domain models.

Extracted from monolithic `models.py` for clarity.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, cast

from django.db import models

from .abstract_models import AbstractMolecularData


class Molecule(models.Model):
    """
    Entidad central que representa una molécula única.

    Uso típico:
        - Se utiliza para almacenar información básica de una molécula (SMILES, InChI, nombre común).
        - Permite asociar datos moleculares concretos mediante métodos como get_data y get_or_create_data.
        - Facilita la integración con workflows y providers para obtener propiedades y variantes.

    Ejemplo de uso:
        mol = Molecule.objects.create(smiles="C1=CC=CC=C1", inchi="InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H", inchikey="UHOVQNZJYSORNB-UHFFFAOYSA-N")
        logp_data, created = mol.get_or_create_data(LogPData, method="user_input", config={"value": 2.5})
    """

    smiles = models.TextField(unique=True)
    """Cadena SMILES que representa la estructura química de la molécula (única)."""
    inchi = models.TextField(unique=True)
    """Cadena InChI que representa la estructura química de la molécula (única)."""
    inchikey = models.CharField(max_length=27, unique=True)
    """Clave InChIKey (27 caracteres, única) para identificación rápida."""
    common_name = models.CharField(max_length=255, blank=True)
    """Nombre común o trivial de la molécula (opcional)."""

    created_at = models.DateTimeField(auto_now_add=True)
    """Fecha y hora de creación de la molécula en la base de datos."""
    updated_at = models.DateTimeField(auto_now=True)
    """Fecha y hora de última actualización de la molécula."""

    def __str__(self):  # pragma: no cover
        """
        Retorna una representación legible de la molécula, útil para debugging y administración.
        Muestra el nombre común (si existe) y el InChIKey.
        """
        return f"{self.common_name or 'Molecule'} ({self.inchikey})"

    def get_data(self, data_class: type[AbstractMolecularData[Any]], *, source: str | None = None,
                 user_tag: str | None = None):  # Return type left unannotated due to Django dynamic queryset generics
        """
        Obtiene un queryset de datos moleculares asociados a esta molécula.
        data_class: clase concreta de AbstractMolecularData (ej: LogPData).
        source: filtra por origen (opcional).
        user_tag: filtra por etiqueta de usuario (opcional).
        Retorna un queryset de instancias de datos moleculares.
        """
        qs = data_class.objects.filter(molecule=self)  
        if source:
            qs = qs.filter(source=source)
        if user_tag:
            qs = qs.filter(user_tag=user_tag)
        return qs

    def get_or_create_data(self, data_class: type[AbstractMolecularData[Any]], *, method: str,
                            config: Dict[str, Any] | None = None, user_tag: str | None = None) -> tuple[AbstractMolecularData[Any], bool]:
        """
        Obtiene o crea un dato molecular asociado a esta molécula.
        data_class: clase concreta de AbstractMolecularData.
        method: método de obtención (ej: "user_input").
        config: configuración para el método (ej: {"value": 2.5}).
        user_tag: etiqueta de usuario (opcional).
        Retorna una tupla (instancia, creado: bool).
        """
        existing = self.get_data(data_class, user_tag=user_tag)
        if existing.exists():
            first = existing.first()
            # existing.exists asegura que first no es None; cast para mypy
            assert first is not None
            return first, False
        instance = data_class.retrieve_data(self, method, config=config, user_tag=user_tag)
        return instance, True

    def ensure_all(self, data_reqs: list[tuple[type[AbstractMolecularData[Any]], str]], *,
                   config_map: Dict[str, Dict[str, Any]] | None = None) -> dict[str, str | None]:
        """
        Garantiza que todos los datos requeridos estén presentes para esta molécula.
        data_reqs: lista de tuplas (clase de dato, método de obtención).
        config_map: diccionario opcional con configuraciones por clase.
        Retorna un diccionario con los nombres de clase y los IDs de datos creados/obtenidos.
        """
        results: dict[str, str | None] = {}
        for cls, method in data_reqs:
            inst, _ = self.get_or_create_data(cls, method=method,
                                              config=(config_map or {}).get(cls.__name__))
            results[cls.__name__] = str(inst.data_id) if inst else None
        return results


class MolecularFamily(models.Model):
    """
    Agrupa moléculas relacionadas para procesamiento conjunto.

    Uso típico:
        - Permite definir familias de moléculas para análisis grupal en workflows.
        - Facilita la ejecución de steps sobre conjuntos de moléculas relacionados.
        - Se utiliza en la orquestación de workflows y selección de variantes de datos.

    Ejemplo de uso:
        fam = MolecularFamily.objects.create(family_id="FAM001", name="Familia Aromáticos")
        fam.members.add(mol1, mol2)
    """

    family_id = models.CharField(max_length=50, unique=True)
    """Identificador único de la familia de moléculas."""
    name = models.CharField(max_length=100)
    """Nombre descriptivo de la familia."""
    description = models.TextField(blank=True)
    """Descripción opcional de la familia."""

    members = models.ManyToManyField(Molecule, related_name="families")
    """Conjunto de moléculas que pertenecen a esta familia."""

    created_at = models.DateTimeField(auto_now_add=True)
    """Fecha y hora de creación de la familia."""
    updated_at = models.DateTimeField(auto_now=True)
    """Fecha y hora de última actualización de la familia."""

    def __str__(self):  # pragma: no cover
        """
        Retorna una representación legible de la familia, útil para debugging y administración.
        Muestra el identificador y el nombre descriptivo.
        """
        return f"{self.family_id} - {self.name}"
