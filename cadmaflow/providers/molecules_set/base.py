"""Abstract base for Molecule Set Providers.

A MoleculeSetProvider encapsulates logic to produce a list/queryset of
``Molecule`` objects (or IDs) given parameters. It is pure Python (no DB model)
so it can be registered dynamically. Steps list which providers they accept.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Sequence

from cadmaflow.models.models import Molecule


class MoleculeSetProvider(ABC):
    """Abstract provider that returns a collection of Molecules.

    Attributes:
        key: Identificador único lógico.
        description: Texto descriptivo corto.
        parameters: Diccionario de configuración concreto para la instancia.
    """
    key: str  # unique identifier (e.g. "initial_selection")
    description: str = ""

    def __init__(self, *, parameters: dict | None = None):
        """Store provider parameters.

        Subclases deberían validar/normalizar aquí.
        """
        self.parameters = parameters or {}

    @abstractmethod
    def produce(self) -> Sequence[Molecule]:  # pragma: no cover - interface
        """Return the produced sequence of Molecules.

        Debe devolver Molecule ya persistidas. Implementaciones pueden crear
        nuevas moléculas si procede.
        """
        raise NotImplementedError

    # Helper util for implementers
    def _by_ids(self, ids: Iterable[int]) -> Sequence[Molecule]:  # pragma: no cover - simple helper
        """Utility helper to fetch Molecules by integer IDs preserving order roughly."""
        return list(Molecule.objects.filter(id__in=list(ids)))
