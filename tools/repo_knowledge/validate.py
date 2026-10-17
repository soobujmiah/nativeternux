"""A minimal JSON Schema subset validator.

SKB's convention (tools/continuity, scripts/) is stdlib-plus-PyYAML, no extra dependencies.
This implements only the subset of JSON Schema draft 2020-12 that
schemas/project-registry.schema.json and schemas/project-event.schema.json actually use:
type, required, properties, additionalProperties, enum, const, pattern, minLength, format
(date-time, UTC and calendar-validated). It is not a general-purpose
validator and should not be reused for a schema outside this pair without re-checking coverage.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_DATE_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []

    if "const" in schema:
        if instance != schema["const"]:
            errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
        return errors

    if "enum" in schema:
        if instance not in schema["enum"]:
            errors.append(f"{path}: {instance!r} not in enum {schema['enum']}")
        return errors

    expected_type = schema.get("type")
    if expected_type is not None:
        types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_matches_type(instance, t) for t in types):
            errors.append(f"{path}: expected type {types}, got {type(instance).__name__}")
            return errors

    if instance is None:
        return errors

    if schema.get("format") == "date-time" and isinstance(instance, str):
        try:
            if not _DATE_TIME_RE.match(instance):
                raise ValueError("not UTC Z form")
            datetime.fromisoformat(instance.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{path}: {instance!r} is not a valid Z-suffixed date-time")

    if "pattern" in schema and isinstance(instance, str) and not re.match(schema["pattern"], instance):
        errors.append(f"{path}: {instance!r} does not match pattern {schema['pattern']!r}")

    if "minLength" in schema and isinstance(instance, str) and len(instance) < schema["minLength"]:
        errors.append(f"{path}: {instance!r} shorter than minLength {schema['minLength']}")

    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    errors.append(f"{path}: unexpected property {key!r}")
        for key, subschema in properties.items():
            if key in instance:
                errors.extend(validate(instance[key], subschema, f"{path}.{key}"))

    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors.extend(validate(item, schema["items"], f"{path}[{i}]"))

    return errors


def _matches_type(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    return False
