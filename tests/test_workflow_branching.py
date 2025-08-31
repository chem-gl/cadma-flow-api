"""Tests for branching, freeze and basic data creation."""
import pytest

from cadmaflow.data_types.qsar import LogPData
from cadmaflow.models.choices import StatusChoices
from cadmaflow.models.models import (
    MolecularFamily,
    Molecule,
    Workflow,
    WorkflowBranch,
    WorkflowExecution,
)


@pytest.mark.django_db
def test_freeze_prevents_modification():
    m = Molecule.objects.create(smiles="C", inchi="InChI=1/C", inchikey="AAAAAAAAAAAAAAAAAAAAAAAI", common_name="Methane")
    d = LogPData.retrieve_data(m, method="user_input", config={"value": 1.23})
    d.freeze(user=None)
    with pytest.raises(RuntimeError):
        d.set_value(2.0)


@pytest.mark.django_db
def test_workflow_branch_and_execution_rewind():
    wf = Workflow.objects.create(key="wf1", name="Test WF")
    branch = WorkflowBranch.objects.create(branch_id="main", name="Main", workflow=wf)
    fam = MolecularFamily.objects.create(family_id="fam1", name="Family 1")
    mol = Molecule.objects.create(smiles="O", inchi="InChI=1/O", inchikey="BBBBBBBBBBBBBBBBBBBBBBB", common_name="Water")
    fam.members.add(mol)
    exec1 = WorkflowExecution.objects.create(execution_id="exec1", name="Exec 1", workflow=wf, branch=branch, status=StatusChoices.PENDING)
    exec1.families.add(fam)
    # Simular paso completado
    se = exec1.start_step(step_id="s1", step_name="Step 1", order=0, frozen_snapshot={}, retrieval_methods={})
    exec1.complete_step(se, results={"ok": True})
    # Rewind / branch
    new_exec = exec1.rewind_to(step_order=0)
    assert new_exec.parent_execution == exec1
    assert new_exec.current_step_index == 1
    assert new_exec.step_executions.count() == 1