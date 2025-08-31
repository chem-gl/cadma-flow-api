import pytest

from cadmaflow.data_types.qsar import (
    AbsorptionData,
    LogPData,
    MutagenicityData,
    ToxicityData,
)
from cadmaflow.models.choices import StatusChoices
from cadmaflow.models.models import (
    MolecularFamily,
    Molecule,
    StepExecution,
    Workflow,
    WorkflowBranch,
    WorkflowExecution,
)
from cadmaflow.models.providers import ProviderExecution
from cadmaflow.utils.serializers import from_json, to_json
from cadmaflow.utils.validators import ValidationError, validate_parameters


@pytest.mark.django_db
def test_qsar_retrieve_and_freeze():
    mol = Molecule.objects.create(smiles="C", inchi="InChI=1/C", inchikey="AAAAAAAAAAAAAAAAAAAAAAAI", common_name="Methane")
    d1 = LogPData.retrieve_data(mol, method="user_input", config={"value": 1.0})
    d2 = ToxicityData.retrieve_data(mol, method="user_input", config={"value": "LOW"})
    AbsorptionData.retrieve_data(mol, method="user_input", config={"value": "HIGH"})
    d4 = MutagenicityData.retrieve_data(mol, method="user_input", config={"value": "NEG"})
    assert float(d1.get_value()) == pytest.approx(1.0)
    assert d2.get_value() == "LOW"
    d1.freeze(user=None)
    with pytest.raises(RuntimeError):
        d1.set_value(2.0)
    # ensure registry retrieval works indirectly via class name
    assert d4.__class__.__name__ == "MutagenicityData"


@pytest.mark.django_db
def test_provider_execution_lifecycle():
    pe = ProviderExecution.objects.create(provider_name="test-provider", provider_kind="PROPERTIES_SET")
    assert pe.status == StatusChoices.PENDING
    pe.mark_started()
    assert pe.status == StatusChoices.RUNNING and pe.started_at is not None
    pe.mark_completed()
    assert pe.status == StatusChoices.COMPLETED and pe.finished_at is not None


@pytest.mark.django_db
def test_workflow_branch_api():
    wf = Workflow.objects.create(key="wfA", name="WF A")
    branched = wf.branch(branch_label="exp1")
    assert branched.branch_of == wf
    assert branched.root_branch in {wf, wf.root_branch}


@pytest.mark.django_db
def test_data_selection_auto_fork_creates_new_execution():
    # Setup base workflow + branch + execution
    wf = Workflow.objects.create(key="wfsel", name="WF Sel")
    branch = WorkflowBranch.objects.create(branch_id="main-sel", name="Main Sel", workflow=wf)
    fam = MolecularFamily.objects.create(family_id="fam-sel", name="Family Sel")
    mol = Molecule.objects.create(smiles="N", inchi="InChI=1/N", inchikey="CCCCCCCCCCCCCCCCCCCCCCCCCC", common_name="Ammonia")
    fam.members.add(mol)
    exec1 = WorkflowExecution.objects.create(execution_id="exec-sel", name="Exec Sel", workflow=wf, branch=branch, status=StatusChoices.PENDING)
    exec1.families.add(fam)
    # Create initial property data and select
    d1 = LogPData.retrieve_data(mol, method="user_input", config={"value": 0.5})
    exec1.select_property_variant(molecule=mol, property_name="logp", data_instance=d1)
    # Simulate a completed step that depended on 'logp'
    StepExecution.objects.create(execution=exec1, step_id="s-logp", step_name="Use LogP", order=0,
                                 input_data_snapshot={}, data_retrieval_methods={}, status=StatusChoices.COMPLETED,
                                 started_at=None, completed_at=None, data_frozen_at=None, input_properties=["logp"],
                                 providers_used=[])
    # Add a new variant; selecting should trigger auto-fork (new execution + branch)
    d2 = LogPData.retrieve_data(mol, method="user_input", config={"value": 0.7})
    exec1.select_property_variant(molecule=mol, property_name="logp", data_instance=d2)
    # Verify an AUTO_FORK event exists
    events = exec1.timeline()
    assert any(e["event_type"] == "AUTO_FORK" for e in events)
    # A new execution should have been created (parent via fork) sharing prefix id pattern
    # (We identify by presence of executions whose parent_execution == exec1)
    # NOTE: branch_execution uses child_executions relation
    child_execs = list(exec1.child_executions.all())
    # Auto-fork uses fork_execution, not branch_execution -> parent is same? It sets parent when forking
    assert child_execs, "Expected a new execution created by auto-fork"


def test_serializers_and_validators():
    payload = {"a": 1, "b": [1, 2, 3]}
    js = to_json(payload)
    assert from_json(js) == payload
    # validator success
    validate_parameters({"x": 1, "y": 2}, {"required": ["x"]})
    # validator failure
    with pytest.raises(ValidationError):
        validate_parameters({"x": 1}, {"required": ["x", "z"]})
