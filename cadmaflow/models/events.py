"""WorkflowEvent model separate module."""
from __future__ import annotations

from django.db import models


class WorkflowEvent(models.Model):
    execution = models.ForeignKey('cadmaflow_models.WorkflowExecution', on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["execution", "event_type"]),
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.execution.execution_id}:{self.event_type}@{self.created_at.isoformat()}"
