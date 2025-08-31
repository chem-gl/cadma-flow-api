"""Generic (de)serialization helpers.

These functions provide lightweight wrappers around JSON (or future formats)
to centralise error handling and potentially plug alternative backends
(orjson, msgpack) without touching domain code.
"""
from __future__ import annotations

import json
from typing import Any


def to_json(data: Any) -> str:
    """Serialize Python object to JSON string raising ValueError on failure."""
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as exc:  # pragma: no cover - simple
        raise ValueError(f"Error serializing data: {exc}") from exc


def from_json(payload: str) -> Any:
    """Deserialize JSON string to Python object raising ValueError on failure."""
    try:
        return json.loads(payload)
    except (TypeError, ValueError) as exc:  # pragma: no cover - simple
        raise ValueError(f"Error deserializing data: {exc}") from exc