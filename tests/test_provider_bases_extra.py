import pytest

from cadmaflow.models import Molecule
from cadmaflow.providers.molecule_sets.base import MoleculeSetProviderBase
from cadmaflow.providers.properties_set.base import PropertyProviderBase


class ValidMoleculeSet(MoleculeSetProviderBase):
    key = "valid_set"
    description = "Returns one molecule descriptor"
    params_spec = {"flag": {"type": "boolean", "default": True}}

    def validate_params(self, params):  # pragma: no cover - trivial
        return params

    def fetch(self, *, params):
        return [{"inchikey": "VALIDDESCINCHIKEYXXXXXXXXXX", "smiles": "C", "common_name": "M1"}]


class SimplePropertyProvider(PropertyProviderBase):
    key = "simple_prop"
    provides = ["logp"]
    description = "Emite logp fijo"
    params_spec = {"value": {"type": "number", "default": 1.0}}

    def compute(self, *, molecule, params):
        yield {"property": "logp", "value": 1.0, "native_type": "FLOAT"}


@pytest.mark.django_db
def test_provider_bases_class_methods_and_run():
    # molecule set provider
    v = ValidMoleculeSet()
    out = v.run(params={})
    assert out and out[0]["inchikey"].startswith("VALIDDESC")
    assert ValidMoleculeSet.get_key() == "valid_set"
    assert "flag" in ValidMoleculeSet.get_spec()

    # property provider run + classmethods
    mol = Molecule.objects.create(smiles="C", inchi="InChI=1/C", inchikey="PROVIDERBASESEXTRATESTVALUEAA", common_name="Methane")
    sp = SimplePropertyProvider()
    results = sp.run(molecule=mol, params={})
    assert results and results[0]["property"] == "logp"
    assert SimplePropertyProvider.get_key() == "simple_prop"
    assert "value" in SimplePropertyProvider.get_spec()
    assert "logp" in SimplePropertyProvider.get_provides()
