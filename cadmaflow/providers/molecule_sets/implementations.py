"""Implementaciones concretas de providers de conjuntos moleculares.

Cada clase simula la obtención de moléculas desde diferentes fuentes.
Todas las variables y métodos están exhaustivamente comentados en español.
"""
from typing import Iterable, TypedDict

from cadmaflow.utils.types import JSONValue

from .base import MoleculeSetProviderBase


class MoleculeDict(TypedDict):
    """
    Estructura de una molécula cruda para los providers.
    inchikey: Identificador único de la molécula (string).
    name: Nombre común de la molécula (string).
    smiles: Representación SMILES de la molécula (string).
    """
    inchikey: str
    name: str
    smiles: str

class UserMoleculeSetProvider(MoleculeSetProviderBase):
    """
    Provider que retorna moléculas proporcionadas por el usuario.
    key: Identificador único del provider.
    description: Descripción legible para humanos.
    params_spec: Especificación de parámetros esperados (vacío en este caso).
    """
    key: str = "user_molecule_set"
    description: str = "Moléculas cargadas manualmente por el usuario."
    params_spec: dict[str, dict[str, JSONValue]] = {}

    def fetch(self, *, params: dict[str, JSONValue]) -> Iterable[dict[str, JSONValue]]:
        """
        Simula la obtención de moléculas del usuario.
        params: Diccionario de parámetros (no usado en este ejemplo).
        Retorna una lista de diccionarios con la estructura de MoleculeDict.
        """
        # Lista simulada de moléculas proporcionadas por el usuario
        return [
            {"inchikey": "AAA111", "name": "Molécula Usuario 1", "smiles": "C1=CC=CC=C1"},
            {"inchikey": "BBB222", "name": "Molécula Usuario 2", "smiles": "CCO"},
        ]

class TestMoleculeSetProvider(MoleculeSetProviderBase):
    """
    Provider que retorna moléculas de la base de datos T.E.S.T.
    key: Identificador único del provider.
    description: Descripción legible para humanos.
    params_spec: Especificación de parámetros esperados (vacío en este caso).
    """
    key: str = "test_molecule_set"
    description: str = "Moléculas de la base T.E.S.T."
    params_spec: dict[str, dict[str, JSONValue]] = {}

    def fetch(self, *, params: dict[str, JSONValue]) -> Iterable[dict[str, JSONValue]]:
        """
        Simula la obtención de moléculas de la base T.E.S.T.
        params: Diccionario de parámetros (no usado en este ejemplo).
        Retorna una lista de diccionarios con la estructura de MoleculeDict.
        """
        return [
            {"inchikey": "CCC333", "name": "Molécula TEST 1", "smiles": "CCN"},
            {"inchikey": "DDD444", "name": "Molécula TEST 2", "smiles": "CNC"},
        ]

class AmbitMoleculeSetProvider(MoleculeSetProviderBase):
    """
    Provider que retorna moléculas de AMBIT.
    key: Identificador único del provider.
    description: Descripción legible para humanos.
    params_spec: Especificación de parámetros esperados (vacío en este caso).
    """
    key: str = "ambit_molecule_set"
    description: str = "Moléculas obtenidas de AMBIT."
    params_spec: dict[str, dict[str, JSONValue]] = {}

    def fetch(self, *, params: dict[str, JSONValue]) -> Iterable[dict[str, JSONValue]]:
        """
        Simula la obtención de moléculas de AMBIT.
        params: Diccionario de parámetros (no usado en este ejemplo).
        Retorna una lista de diccionarios con la estructura de MoleculeDict.
        """
        return [
            {"inchikey": "EEE555", "name": "Molécula AMBIT 1", "smiles": "CCCl"},
            {"inchikey": "FFF666", "name": "Molécula AMBIT 2", "smiles": "CCBr"},
        ]
