"""Abstract base for Property (Data) Set Providers.

A PropertySetProvider receives a prepared list of Molecules and is responsible
for producing one or more instances of ``AbstractMolecularData`` for each
molecule (or a subset) for a defined list of properties.

It returns a flat list of created data instances (persisted already) so that
Steps can register variants and optionally select active ones.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence, Type

from cadmaflow.models.abstract_models import AbstractMolecularData
from cadmaflow.models.models import Molecule


class PropertySetProvider(ABC):
    """Abstract provider that generates property data for a set of molecules.

    Attributes:
        key: Identificador lógico único.
        description: Descripción corta para UI.
        produced_data_classes: Lista de clases de datos que puede producir.
        molecules: Lista de Molecule sobre las que trabaja la instancia.
        parameters: Configuración específica (validada externamente o por la subclase).
    """
    key: str
    description: str = ""
    produced_data_classes: Sequence[Type[AbstractMolecularData]] = ()

    def __init__(self, molecules: Sequence[Molecule], *, parameters: dict | None = None):
        """Store molecules and parameters for the provider run."""
        self.molecules = list(molecules)
        self.parameters = parameters or {}

    @abstractmethod
    def produce(self) -> List[AbstractMolecularData]:  # pragma: no cover - interface
        """Produce and persist data objects.

        Debe persistir cada instancia antes de retornarla.
        """
        raise NotImplementedError

    # Helper to produce via a simple mapping {Molecule: {cls: config}}
    def _produce_simple(self, mapping: dict[Molecule, dict[Type[AbstractMolecularData], dict]]):  # pragma: no cover - helper
        created: List[AbstractMolecularData] = []
        for mol, cls_cfg in mapping.items():
            for cls, cfg in cls_cfg.items():
                method = cfg.get("method") or "user_input"
                config = cfg.get("config") or {}
                obj = cls.retrieve_data(molecule=mol, method=method, config=config, user_tag=cfg.get("tag"))
                created.append(obj)
        return created
