import pytest

from cadmaflow.models import Molecule
from cadmaflow.providers.molecule_sets.base import MoleculeSetProviderBase
from cadmaflow.providers.properties_set.base import PropertyProviderBase


def test_molecule_set_provider_requires_key():
    with pytest.raises(ValueError):
        # Definir e instanciar una subclase inválida inmediatamente
        class _X(MoleculeSetProviderBase):  # noqa: N801 - nombre interno para test
            key = ""

            def fetch(self, *, params):  # pragma: no cover - no se ejecuta
                return []

        _X()  # dispara ValueError en __init_subclass__


class _SimpleMoleculeSet(MoleculeSetProviderBase):
    key = "simple_set"
    description = "devuelve lista fija"

    def fetch(self, *, params):
        return [
            {"inchikey": "IK1", "smiles": "C", "common_name": "Methane"},
            {"inchikey": "IK2", "smiles": "O", "common_name": "Water"},
        ]


def test_molecule_set_provider_run_creates_dicts():
    prov = _SimpleMoleculeSet()
    out = prov.run(params={})
    assert len(out) == 2 and all("inchikey" in d for d in out)


class _StaticLogPProvider(PropertyProviderBase):
    key = "static_logp"
    description = "Asigna logp fijo"
    provides = ["logp"]

    def compute(self, *, molecule, params):
        # Emite un único dict con valor fijo
        yield {"property": "logp", "value": 1.0, "native_type": "FLOAT"}


def test_property_provider_validation_requires_provides():
    with pytest.raises(ValueError):
        class _Bad(PropertyProviderBase):  # noqa: N801
            key = "bad"
            provides: list[str] = []

            def compute(self, *, molecule, params):  # pragma: no cover
                yield {}

        _Bad()


def test_property_provider_run(db):
    mol = Molecule.objects.create(smiles="C", inchi="InChI=1/C", inchikey="AAAAAAAAAAAAAAAAAAAAAAAI", common_name="Methane")
    prov = _StaticLogPProvider()
    out = prov.run(molecule=mol, params={})
    assert out and out[0]["property"] == "logp"
    val = out[0]["value"]
    assert abs(val - 1.0) < 1e-9
