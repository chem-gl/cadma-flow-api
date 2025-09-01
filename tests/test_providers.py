"""Tests simples para los nuevos providers de conjuntos moleculares y propiedades.
Todos los comentarios y variables están en español.
"""
from cadmaflow.models.molecule import Molecule  # Importa el modelo de molécula
from cadmaflow.providers.molecule_sets.implementations import (
    AmbitMoleculeSetProvider,  # Provider de AMBIT
    TestMoleculeSetProvider,  # Provider de TEST
    UserMoleculeSetProvider,  # Provider de usuario
)
from cadmaflow.providers.properties_set.implementations import (
    LogPCalcProvider,  # Provider de propiedades
)

# Test para UserMoleculeSetProvider

def test_user_molecule_set_provider() -> None:
    """
    Verifica que el provider de usuario retorna la estructura esperada.
    Se espera una lista de dos moléculas con los campos correctos.
    """
    provider = UserMoleculeSetProvider()  # Instancia el provider de usuario
    resultados = list(provider.fetch(params={}))  # Obtiene la lista de moléculas simuladas
    assert len(resultados) == 2  # Verifica que hay dos moléculas
    for mol in resultados:
        assert "inchikey" in mol  # Verifica que existe el campo inchikey
        assert "name" in mol      # Verifica que existe el campo name
        assert "smiles" in mol    # Verifica que existe el campo smiles

# Test para TestMoleculeSetProvider

def test_test_molecule_set_provider() -> None:
    """
    Verifica que el provider de TEST retorna la estructura esperada.
    Se espera una lista de dos moléculas con los campos correctos.
    """
    provider = TestMoleculeSetProvider()  # Instancia el provider de TEST
    resultados = list(provider.fetch(params={}))  # Obtiene la lista de moléculas simuladas
    assert len(resultados) == 2  # Verifica que hay dos moléculas
    for mol in resultados:
        assert "inchikey" in mol  # Verifica que existe el campo inchikey
        assert "name" in mol      # Verifica que existe el campo name
        assert "smiles" in mol    # Verifica que existe el campo smiles

# Test para AmbitMoleculeSetProvider

def test_ambit_molecule_set_provider() -> None:
    """
    Verifica que el provider de AMBIT retorna la estructura esperada.
    Se espera una lista de dos moléculas con los campos correctos.
    """
    provider = AmbitMoleculeSetProvider()  # Instancia el provider de AMBIT
    resultados = list(provider.fetch(params={}))  # Obtiene la lista de moléculas simuladas
    assert len(resultados) == 2  # Verifica que hay dos moléculas
    for mol in resultados:
        assert "inchikey" in mol  # Verifica que existe el campo inchikey
        assert "name" in mol      # Verifica que existe el campo name
        assert "smiles" in mol    # Verifica que existe el campo smiles

# Test para LogPCalcProvider

def test_logp_calc_provider() -> None:
    """
    Verifica que el provider de propiedades retorna un resultado simulado correcto.
    Se espera un solo resultado con los campos correctos y el tipo adecuado.
    """
    provider = LogPCalcProvider()  # Instancia el provider de propiedades
    # Creamos una molécula dummy para el test
    mol = Molecule(
        smiles="CCO",  # Cadena SMILES de la molécula
        inchi="InChI=1S/CCO",  # Cadena InChI
        inchikey="DUMMYKEY",  # Identificador único
        common_name="Etanol"   # Nombre común
    )
    resultados = list(provider.compute(molecule=mol, params={}))  # Obtiene el resultado simulado
    assert len(resultados) == 1  # Verifica que hay un solo resultado
    res = resultados[0]
    assert res["property"] == "logP"  # Verifica el nombre de la propiedad
    assert isinstance(res["value"], float)  # Verifica que el valor es float
    assert res["native_type"] == "FLOAT"  # Verifica el tipo nativo
    assert "extra" in res  # Verifica que existe el campo extra
