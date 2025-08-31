import pytest

from cadmaflow.data_types.qsar import LogPData
from cadmaflow.models import (
    MolecularFamily,
    Molecule,
    Workflow,
    WorkflowBranch,
    WorkflowExecution,
)
from cadmaflow.workflows.base import FlowBase, FlowMeta
from cadmaflow.workflows.steps.base import BaseStep


class DummyStep(BaseStep):
    step_id = "dummy"
    name = "Dummy"
    description = "Test step"
    order = 1

    def _process_step(self, input_data, step_execution, parameters):
        return {"seen": bool(input_data)}


class NeedsLogPStep(BaseStep):
    step_id = "needs_logp"
    name = "Needs LogP"
    description = "Requires logp data"
    order = 0
    required_data_classes = (LogPData,)

    def _process_step(self, input_data, step_execution, parameters):  # pragma: no cover - not reached in failure test
        return {}


class SimpleFlow(FlowBase):
    meta = FlowMeta(flow_id="flow1", name="Flow 1")
    steps = (DummyStep,)


@pytest.mark.django_db
def test_flowbase_run_simple():
    wf = Workflow.objects.create(key="wf-flow", name="WF Flow")
    branch = WorkflowBranch.objects.create(branch_id="main-flow", name="Main Flow", workflow=wf)
    fam = MolecularFamily.objects.create(family_id="fam-flow", name="Family Flow")
    mol = Molecule.objects.create(smiles="C", inchi="InChI=1/C", inchikey="FLOWFLOWFLOWFLOWFLOWFLOWFL", common_name="Methane")
    fam.members.add(mol)
    exec1 = WorkflowExecution.objects.create(execution_id="exec-flow", name="Exec Flow", workflow=wf, branch=branch)
    exec1.families.add(fam)
    flow = SimpleFlow(exec1)
    flow.run()
    assert exec1.step_executions.filter(step_id="dummy").count() == 1
    # second run with auto_skip should not create a new StepExecution
    flow.run()
    assert exec1.step_executions.filter(step_id="dummy").count() == 1


@pytest.mark.django_db
def test_flowbase_can_execute_failure_and_success():
    wf = Workflow.objects.create(key="wf-needs", name="WF Needs")
    branch = WorkflowBranch.objects.create(branch_id="main-needs", name="Main Needs", workflow=wf)
    fam = MolecularFamily.objects.create(family_id="fam-needs", name="Family Needs")
    mol = Molecule.objects.create(smiles="O", inchi="InChI=1/O", inchikey="NEEDSNEEDSNEEDSNEEDSNEEDSNE", common_name="Water")
    fam.members.add(mol)
    exec1 = WorkflowExecution.objects.create(execution_id="exec-needs", name="Exec Needs", workflow=wf, branch=branch)
    exec1.families.add(fam)

    class FlowNeeds(FlowBase):
        meta = FlowMeta(flow_id="needs", name="Needs")
        steps = (NeedsLogPStep,)

    flow = FlowNeeds(exec1)
    with pytest.raises(RuntimeError):
        flow.run()
    # Provide retrieval method then run
    exec1.set_data_retrieval_method(family_id=fam.family_id, data_class_name="LogPData", method="user_input")
    flow.run()
    assert exec1.step_executions.filter(step_id="needs_logp").exists()


@pytest.mark.django_db
def test_step_progress():
    wf = Workflow.objects.create(key="wf-prog", name="WF Prog")
    branch = WorkflowBranch.objects.create(branch_id="main-prog", name="Main Prog", workflow=wf)
    fam = MolecularFamily.objects.create(family_id="fam-prog", name="Family Prog")
    mol1 = Molecule.objects.create(smiles="N", inchi="InChI=1/N", inchikey="PROGRESSMOLONEAAAAAAAAAAAAA", common_name="N1")
    mol2 = Molecule.objects.create(smiles="NN", inchi="InChI=1/NN", inchikey="PROGRESSMOLTWOAAAAAAAAAAAAA", common_name="N2")
    fam.members.add(mol1, mol2)
    exec1 = WorkflowExecution.objects.create(execution_id="exec-prog", name="Exec Prog", workflow=wf, branch=branch)
    exec1.families.add(fam)
    exec1.set_data_retrieval_method(fam.family_id, "LogPData", "user_input")

    class PStep(BaseStep):
        step_id = "p"
        name = "Progress"
        description = "Progress test"
        order = 0
        required_data_classes = (LogPData,)
        def _process_step(self, input_data, step_execution, parameters):  # pragma: no cover
            return {}

    step = PStep()
    progress = step.get_progress(exec1)
    assert 0 < progress <= 1
