import pytest

from cadmaflow.models import (
    MolecularFamily,
    Molecule,
    Workflow,
    WorkflowBranch,
    WorkflowExecution,
)
from cadmaflow.workflows.base import FlowBase, FlowMeta
from cadmaflow.workflows.steps.base import BaseStep


class FailingStep(BaseStep):
    step_id = 'fail'
    name = 'Failing'
    description = 'Fails intentionally'
    order = 0

    def _process_step(self, input_data, step_execution, parameters):  # noqa: D401
        raise ValueError('boom')


class SimpleFailFlow(FlowBase):
    meta = FlowMeta(flow_id='f', name='FailFlow')
    steps = (FailingStep,)


@pytest.mark.django_db
def test_step_execution_failure_marks_failed():
    wf = Workflow.objects.create(key='wf-fail', name='WF Fail')
    branch = WorkflowBranch.objects.create(branch_id='main-fail', name='Main Fail', workflow=wf)
    fam = MolecularFamily.objects.create(family_id='fam-fail', name='Family Fail')
    mol = Molecule.objects.create(smiles='C', inchi='InChI=1/C', inchikey='STEPFAILTESTVALUEAAAAAAA', common_name='Methane')
    fam.members.add(mol)
    exec1 = WorkflowExecution.objects.create(execution_id='exec-fail', name='Exec Fail', workflow=wf, branch=branch)
    exec1.families.add(fam)
    flow = SimpleFailFlow(exec1)
    with pytest.raises(ValueError):
        flow.run()
    se = exec1.step_executions.get(step_id='fail')
    assert se.status == 'FAILED'
    assert se.results.get('error') == 'boom'