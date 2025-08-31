"""Molecule and MolecularFamily domain models.

Extracted from monolithic `models.py` for clarity.
"""
from __future__ import annotations

from django.db import models

from .abstract_models import AbstractMolecularData


class Molecule(models.Model):
    """Entidad central que representa una molécula única."""

    smiles = models.TextField(unique=True)
    inchi = models.TextField(unique=True)
    inchikey = models.CharField(max_length=27, unique=True)
    common_name = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # pragma: no cover
        return f"{self.common_name or 'Molecule'} ({self.inchikey})"

    def get_data(self, data_class: type[AbstractMolecularData], *, source: str | None = None,
                 user_tag: str | None = None):
        qs = data_class.objects.filter(molecule=self)
        if source:
            qs = qs.filter(source=source)
        if user_tag:
            qs = qs.filter(user_tag=user_tag)
        return qs

    def get_or_create_data(self, data_class: type[AbstractMolecularData], *, method: str,
                            config: dict | None = None, user_tag: str | None = None):
        existing = self.get_data(data_class, user_tag=user_tag)
        if existing.exists():
            return existing.first(), False
        instance = data_class.retrieve_data(self, method, config=config, user_tag=user_tag)
        return instance, True

    def ensure_all(self, data_reqs: list[tuple[type[AbstractMolecularData], str]], *,
                   config_map: dict | None = None):
        results: dict[str, str | None] = {}
        for cls, method in data_reqs:
            inst, _ = self.get_or_create_data(cls, method=method,
                                              config=(config_map or {}).get(cls.__name__))
            results[cls.__name__] = str(inst.data_id) if inst else None
        return results


class MolecularFamily(models.Model):
    """Agrupa moléculas relacionadas para procesamiento conjunto."""

    family_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    members = models.ManyToManyField(Molecule, related_name="families")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # pragma: no cover
        return f"{self.family_id} - {self.name}"
