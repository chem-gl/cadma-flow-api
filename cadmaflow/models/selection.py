"""Active property variant selection model."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class DataSelection(models.Model):
    execution = models.ForeignKey('cadmaflow_models.WorkflowExecution', on_delete=models.CASCADE, related_name="data_selections")
    branch = models.ForeignKey('cadmaflow_models.WorkflowBranch', on_delete=models.CASCADE, related_name="data_selections")
    molecule = models.ForeignKey('cadmaflow_models.Molecule', on_delete=models.CASCADE, related_name="data_selections")
    property_name = models.CharField(max_length=100)
    data_class = models.CharField(max_length=150)
    data_id = models.UUIDField()
    provider_execution = models.ForeignKey('cadmaflow_models.ProviderExecution', on_delete=models.SET_NULL, null=True, blank=True)
    selected_at = models.DateTimeField(auto_now_add=True)
    selected_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('execution', 'branch', 'molecule', 'property_name')
        indexes = [
            models.Index(fields=['molecule', 'property_name']),
            models.Index(fields=['property_name', 'provider_execution']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Sel:{self.property_name} -> {self.data_class}({self.data_id})"
