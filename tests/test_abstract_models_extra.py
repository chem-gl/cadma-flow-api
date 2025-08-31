import pytest
from django.contrib.auth import get_user_model

from cadmaflow.data_types.qsar import LogPData


@pytest.mark.django_db
def test_abstract_model_set_and_freeze():
    user_model = get_user_model()
    user = user_model.objects.create(username='u1')
    # Create instance via retrieval
    mol_cls = pytest.importorskip('cadmaflow.models').Molecule  # type: ignore[attr-defined]
    mol = mol_cls.objects.create(smiles='CC', inchi='InChI=1/CC', inchikey='ABSTRACTMODELTESTVALAAAAAAA', common_name='Ethane')
    d = LogPData.retrieve_data(mol, method='user_input', config={'value': 2.0})
    # set_value type mismatch
    with pytest.raises(ValueError):
        d.set_value('bad')  # type: ignore[arg-type]
    # Proper set and freeze
    d.set_value(3.5)
    d.freeze(user)
    with pytest.raises(RuntimeError):
        d.set_value(4.0)


@pytest.mark.django_db
def test_abstract_model_string_repr_error_path(monkeypatch):
    mol_cls = pytest.importorskip('cadmaflow.models').Molecule  # type: ignore[attr-defined]
    mol = mol_cls.objects.create(smiles='CCC', inchi='InChI=1/CCC', inchikey='ABSTRACTMODELREPRTESTAAAAAA', common_name='Propane')
    d = LogPData.retrieve_data(mol, method='user_input', config={'value': 1.0})
    # Corrupt value_json to force deserialize error
    d.value_json = '{bad json}'
    d.save(update_fields=['value_json'])
    s = str(d)
    assert 'Error:' in s