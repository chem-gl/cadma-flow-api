"""Provider related persistent models.

Minimal implementation restored after refactor to ensure ForeignKey targets
exist for AbstractMolecularData.provider_execution and DataSelection.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from .choices import StatusChoices


class ProviderExecution(models.Model):
    """Tracks a single run of a provider (molecule set or properties set)."""

    PROVIDER_KIND_CHOICES = [
        ("MOLECULE_SET", "Molecule Set"),
        ("PROPERTIES_SET", "Properties Set"),
    ]

    provider_name = models.CharField(max_length=100)
    provider_kind = models.CharField(max_length=20, choices=PROVIDER_KIND_CHOICES)
    provider_version = models.CharField(max_length=50, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider_name", "provider_kind"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):  # pragma: no cover - trivial
        return f"{self.provider_name} ({self.provider_kind}) [{self.status}]"

    # --- Lifecycle helpers -------------------------------------------------
    def mark_started(self) -> None:
        self.status = StatusChoices.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self) -> None:
        self.status = StatusChoices.COMPLETED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    def mark_failed(self, message: str) -> None:
        self.status = StatusChoices.FAILED
        self.error_message = message
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "error_message", "finished_at"])
