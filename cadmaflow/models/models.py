"""Re-export shim for backward compatibility.

The original monolithic models file has been split into modular files:
 - molecule.py
 - workflow.py
 - execution.py
 - step_execution.py
 - events.py
 - selection.py

Keep this shim so existing import paths (`from cadmaflow.models.models import X`)
remain valid. Remove only after refactoring all downstream imports.
"""

from . import providers  # noqa: F401
from .events import WorkflowEvent  # noqa: F401
from .execution import WorkflowExecution  # noqa: F401
from .molecule import MolecularFamily, Molecule  # noqa: F401
from .selection import DataSelection  # noqa: F401
from .step_execution import StepExecution  # noqa: F401
from .workflow import Workflow, WorkflowBranch  # noqa: F401

__all__ = [
    "Workflow",
    "WorkflowBranch",
    "Molecule",
    "MolecularFamily",
    "WorkflowExecution",
    "StepExecution",
    "WorkflowEvent",
    "DataSelection",
]