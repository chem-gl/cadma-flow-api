"""Workflow blueprint and branching models."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from .choices import StatusChoices

User = get_user_model()


class Workflow(models.Model):
    """Blueprint lógico de un flujo."""

    key = models.CharField(max_length=50, unique=True, help_text="Identificador estable")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)

    branch_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_branches')
    root_branch = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='descendants')
    branch_label = models.CharField(max_length=100, blank=True)

    frozen_at = models.DateTimeField(null=True, blank=True)
    frozen_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='frozen_workflows')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def save(self, *args, **kwargs):  # pragma: no cover
        if self.pk is None and self.branch_of and not self.root_branch:
            self.root_branch = self.branch_of.root_branch or self.branch_of
        super().save(*args, **kwargs)

    def freeze(self, user):  # pragma: no cover
        self.frozen_at = timezone.now()
        self.frozen_by = user
        self.save(update_fields=["frozen_at", "frozen_by", "updated_at"])

    def branch(self, *, branch_label: str | None = None, reason: str | None = None, user=None) -> 'Workflow':
        # Ensure uniqueness even when multiple branches are created within the same second.
        base = f"{self.key}-br-{int(timezone.now().timestamp())}"
        candidate = base
        suffix = 0
        while Workflow.objects.filter(key=candidate).exists():  # pragma: no cover - loop rarely iterates >1
            suffix += 1
            candidate = f"{base}-{suffix}"
        new_wf = Workflow.objects.create(
            key=candidate,
            name=self.name,
            description=self.description,
            status=StatusChoices.PENDING,
            branch_of=self,
            root_branch=self.root_branch or self,
            branch_label=branch_label or f"branch-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        )
        return new_wf

    def __str__(self):  # pragma: no cover
        return f"WF:{self.key} - {self.name}"


class WorkflowBranch(models.Model):
    """Rama lógica para selección de variantes de datos."""

    branch_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    workflow = models.ForeignKey('cadmaflow_models.Workflow', on_delete=models.CASCADE, related_name='branches')
    parent_branch = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    branch_reason = models.TextField(blank=True)
    data_selection_preferences = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # pragma: no cover
        return f"{self.branch_id} - {self.name}"

    def fork(self, *, new_branch_id: str, name: str, reason: str | None = None,
             preference_overrides: dict | None = None):
        prefs = dict(self.data_selection_preferences)
        if preference_overrides:
            prefs.update(preference_overrides)
        # Guarantee uniqueness if caller accidentally reuses an id (fast in sqlite/memory tests)
        candidate = new_branch_id
        counter = 0
        while WorkflowBranch.objects.filter(branch_id=candidate).exists():  # pragma: no cover - rarely loops >1
            counter += 1
            candidate = f"{new_branch_id}-{counter}"
        return WorkflowBranch.objects.create(
            branch_id=candidate,
            name=name,
            description=self.description,
            workflow=self.workflow,
            parent_branch=self,
            branch_reason=reason or "",
            data_selection_preferences=prefs,
        )
