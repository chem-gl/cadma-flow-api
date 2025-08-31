import pytest

from cadmaflow.data_types.qsar import LogPData, ToxicityData
from cadmaflow.models import Molecule


@pytest.mark.django_db
def test_molecule_data_helpers():
    mol = Molecule.objects.create(smiles="C", inchi="InChI=1/C", inchikey="MOLECULEHELPERTESTVALUEAAAAAA", common_name="Methane")
    inst1 = LogPData.retrieve_data(mol, method="user_input", config={"value": 2.5})
    qs = mol.get_data(LogPData)
    assert qs.count() == 1
    inst2, created = mol.get_or_create_data(LogPData, method="user_input", config={"value": 2.5})
    assert not created and inst1.data_id == inst2.data_id
    results = mol.ensure_all([(ToxicityData, "user_input")], config_map={"ToxicityData": {"value": "LOW"}})
    assert results.get("ToxicityData")
