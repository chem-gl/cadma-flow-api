"""StepExecution model separate module."""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from .choices import StatusChoices


class StepExecution(models.Model):
    execution = models.ForeignKey('cadmaflow_models.WorkflowExecution', on_delete=models.CASCADE, related_name='step_executions')
    step_id = models.CharField(max_length=100)
    step_name = models.CharField(max_length=200)
    order = models.IntegerField()
    input_data_snapshot = models.JSONField(default=dict)
    data_retrieval_methods = models.JSONField(default=dict)
    results = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    data_frozen_at = models.DateTimeField(blank=True, null=True)
    input_signature = models.CharField(max_length=64, blank=True)
    input_properties = models.JSONField(default=list, blank=True)
    providers_used = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['order', 'started_at']

    def __str__(self):  # pragma: no cover
        return f"{self.execution.execution_id} - {self.step_name} ({self.status})"

    def mark_failed(self, message: str):
        self.status = StatusChoices.FAILED
        self.results = {"error": message}
        self.completed_at = timezone.now()
        self.save()
        self.execution.log_event(event_type="STEP_FAILED", details={"step_id": self.step_id, "error": message})

    @property
    def input_snapshot(self):  # pragma: no cover
        return self.input_data_snapshot

    @input_snapshot.setter
    def input_snapshot(self, value):  # pragma: no cover
        self.input_data_snapshot = value
