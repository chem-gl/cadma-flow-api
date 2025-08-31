"""Validation helpers (JSON schema lightweight stub).

In a future iteration we can integrate `jsonschema`. For now we keep a
minimal interface so callers can rely on a consistent error contract.
"""
from __future__ import annotations

from typing import Any, Mapping


class ValidationError(Exception):
    """Raised when validation fails."""


def validate_parameters(parameters: Mapping[str, Any], schema: Mapping[str, Any]) -> None:  # pragma: no cover - trivial
    """Very light validation: ensures required keys exist if 'required' list provided."""
    required = schema.get("required", []) if isinstance(schema, Mapping) else []
    missing = [k for k in required if k not in parameters]
    if missing:
        raise ValidationError(f"Missing required parameters: {missing}")