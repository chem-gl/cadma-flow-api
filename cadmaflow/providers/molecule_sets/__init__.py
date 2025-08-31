"""Molecule set provider package.

Concrete providers should subclass `MoleculeSetProvider` and implement
`produce()` returning a sequence of persisted `Molecule` instances.
"""
from .base import MoleculeSetProvider  # noqa: F401
