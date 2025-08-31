"""Common strongly-typed aliases used across the project.

Provides JSON compatible recursive type definitions to avoid pervasive
usage of ``Any`` while keeping flexibility for dynamic payloads.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, MutableMapping, Sequence, Tuple, Union

# Recursive JSON value type
JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, "JSONDict", List["JSONValue"]]
JSONDict = Dict[str, JSONValue]

# Common parameter / config aliases
Parameters = Mapping[str, JSONValue]
MutableParameters = MutableMapping[str, JSONValue]
JSONMapping = Mapping[str, JSONValue]
JSONSequence = Sequence[JSONValue]
JSONTuple = Tuple[JSONValue, ...]

__all__ = [
    "JSONPrimitive",
    "JSONValue",
    "JSONDict",
    "JSONMapping",
    "JSONSequence",
    "JSONTuple",
    "Parameters",
    "MutableParameters",
]
