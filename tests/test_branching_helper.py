import pytest

from cadmaflow.models import (
    MolecularFamily,
    Molecule,
    Workflow,
    WorkflowBranch,
    WorkflowExecution,
)
from cadmaflow.utils.branching import clone_step_executions


@pytest.mark.django_db
def test_clone_step_executions():
    wf = Workflow.objects.create(key="wf-br", name="WF BR")
    branch = WorkflowBranch.objects.create(branch_id="main-br", name="Main BR", workflow=wf)
    fam = MolecularFamily.objects.create(family_id="fam-br", name="Family BR")
    mol = Molecule.objects.create(smiles="C", inchi="InChI=1/C", inchikey="BRANCHINGHELPERTESTVALUEAAA", common_name="Methane")
    fam.members.add(mol)
    exec1 = WorkflowExecution.objects.create(execution_id="exec-br1", name="Exec BR1", workflow=wf, branch=branch)
    exec1.families.add(fam)
    se = exec1.start_step(step_id="s1", step_name="S1", order=0, frozen_snapshot={}, retrieval_methods={})
    exec1.complete_step(se, results={"ok": True})
    exec2 = WorkflowExecution.objects.create(execution_id="exec-br2", name="Exec BR2", workflow=wf, branch=branch)
    exec2.families.add(fam)
    clone_step_executions(exec1.step_executions.all(), new_execution=exec2)
    assert exec2.step_executions.count() == 1
