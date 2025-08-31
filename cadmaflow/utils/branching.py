"""Branching helper utilities.

Contains pure functions to assist with snapshot copying or branch diffing.
Currently minimal; expanded as branching logic grows.
"""
from __future__ import annotations

from typing import Iterable

from cadmaflow.models.models import StepExecution


def clone_step_executions(step_executions: Iterable[StepExecution], *, new_execution) -> None:  # pragma: no cover - helper
    """Clone given completed StepExecution records into a new execution."""
    for se in step_executions:
        StepExecution.objects.create(
            execution=new_execution,
            step_id=se.step_id,
            step_name=se.step_name,
            order=se.order,
            input_data_snapshot=se.input_data_snapshot,
            data_retrieval_methods=se.data_retrieval_methods,
            results=se.results,
            status=se.status,
            started_at=se.started_at,
            completed_at=se.completed_at,
            data_frozen_at=se.data_frozen_at,
            input_signature=se.input_signature,
            input_properties=se.input_properties,
            providers_used=se.providers_used,
        )