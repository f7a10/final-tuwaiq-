from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from dcel_editor import PlanRevision, RevisionResult, apply_transaction


@dataclass(frozen=True)
class Clarification:
    code: str
    question: str
    options: tuple[str, ...]


@dataclass(frozen=True)
class EditIntent:
    status: str
    base_revision_id: str | None
    commands: tuple[dict[str, object], ...] = ()
    clarifications: tuple[Clarification, ...] = ()
    errors: tuple[str, ...] = ()


_TOP_LEVEL_FIELDS = {
    "schema_version",
    "base_revision_id",
    "commands",
    "clarifications",
}
_COMMAND_FIELDS = {
    "move_wall": {"type", "wall_run_id", "offset_mm"},
    "move_opening": {"type", "opening_id", "station_mm"},
}


def openrouter_request_contract(
    current_revision_id: str,
) -> dict[str, object]:
    move_wall_schema = {
        "type": "object",
        "properties": {
            "type": {"const": "move_wall"},
            "wall_run_id": {
                "type": "string",
                "description": "Existing stable wall-run identifier",
            },
            "offset_mm": {
                "type": "integer",
                "description": "Signed wall displacement in integer millimetres",
            },
        },
        "required": ["type", "wall_run_id", "offset_mm"],
        "additionalProperties": False,
    }
    move_opening_schema = {
        "type": "object",
        "properties": {
            "type": {"const": "move_opening"},
            "opening_id": {
                "type": "string",
                "description": "Existing stable opening identifier",
            },
            "station_mm": {
                "type": "integer",
                "description": "Opening centre station on its wall run in millimetres",
            },
        },
        "required": ["type", "opening_id", "station_mm"],
        "additionalProperties": False,
    }
    clarification_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "question": {"type": "string"},
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 4,
                "uniqueItems": True,
            },
        },
        "required": ["code", "question", "options"],
        "additionalProperties": False,
    }
    schema = {
        "type": "object",
        "properties": {
            "schema_version": {"const": "emad.edit-intent.v1"},
            "base_revision_id": {"const": current_revision_id},
            "commands": {
                "type": "array",
                "items": {"anyOf": [move_wall_schema, move_opening_schema]},
                "maxItems": 20,
            },
            "clarifications": {
                "type": "array",
                "items": clarification_schema,
                "maxItems": 1,
            },
        },
        "required": [
            "schema_version",
            "base_revision_id",
            "commands",
            "clarifications",
        ],
        "additionalProperties": False,
    }
    return {
        "provider": {"require_parameters": True},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "emad_edit_intent_v1",
                "strict": True,
                "schema": schema,
            },
        },
    }


class _DuplicateKeyError(ValueError):
    pass


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for key, value in pairs:
        if key in parsed:
            raise _DuplicateKeyError(key)
        parsed[key] = value
    return parsed


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _rejected(
    *errors: str,
    base_revision_id: str | None = None,
) -> EditIntent:
    return EditIntent(
        status="rejected",
        base_revision_id=base_revision_id,
        errors=tuple(errors),
    )


def validate_edit_intent(
    raw_payload: str,
    *,
    current_revision_id: str,
) -> EditIntent:
    try:
        payload: Any = json.loads(
            raw_payload,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except _DuplicateKeyError as error:
        return _rejected(f"Duplicate JSON key: {error}")
    except (TypeError, json.JSONDecodeError) as error:
        return _rejected(f"Invalid JSON: {error}")
    if not isinstance(payload, dict):
        return _rejected("Intent payload must be a JSON object")

    unknown_top_level = sorted(set(payload) - _TOP_LEVEL_FIELDS)
    if unknown_top_level:
        return _rejected(
            "Unknown top-level fields: " + ", ".join(unknown_top_level),
            base_revision_id=payload.get("base_revision_id"),
        )
    missing_top_level = sorted(_TOP_LEVEL_FIELDS - set(payload))
    if missing_top_level:
        return _rejected(
            "Missing top-level fields: " + ", ".join(missing_top_level),
            base_revision_id=payload.get("base_revision_id"),
        )
    if payload["schema_version"] != "emad.edit-intent.v1":
        return _rejected(
            "Unsupported schema_version",
            base_revision_id=payload.get("base_revision_id"),
        )
    base_revision_id = payload["base_revision_id"]
    if not isinstance(base_revision_id, str):
        return _rejected("base_revision_id must be a string")
    if base_revision_id != current_revision_id:
        return _rejected(
            "Stale base revision",
            base_revision_id=base_revision_id,
        )
    commands = payload["commands"]
    clarifications = payload["clarifications"]
    if not isinstance(commands, list):
        return _rejected(
            "commands must be an array",
            base_revision_id=base_revision_id,
        )
    if len(commands) > 20:
        return _rejected(
            "commands must contain at most 20 items",
            base_revision_id=base_revision_id,
        )
    if not isinstance(clarifications, list):
        return _rejected(
            "clarifications must be an array",
            base_revision_id=base_revision_id,
        )
    if len(clarifications) > 1:
        return _rejected(
            "Intent may contain at most one clarification question",
            base_revision_id=base_revision_id,
        )

    normalized_commands: list[dict[str, object]] = []
    for index, command in enumerate(commands, start=1):
        if not isinstance(command, dict):
            return _rejected(
                f"Command {index} must be an object",
                base_revision_id=base_revision_id,
            )
        command_type = command.get("type")
        if command_type not in _COMMAND_FIELDS:
            return _rejected(
                f"Command {index} has unsupported type {command_type}",
                base_revision_id=base_revision_id,
            )
        expected_fields = _COMMAND_FIELDS[str(command_type)]
        if set(command) != expected_fields:
            unknown = sorted(set(command) - expected_fields)
            missing = sorted(expected_fields - set(command))
            details = []
            if unknown:
                details.append("unknown=" + ",".join(unknown))
            if missing:
                details.append("missing=" + ",".join(missing))
            return _rejected(
                f"Command {index} fields are invalid: " + "; ".join(details),
                base_revision_id=base_revision_id,
            )
        if command_type == "move_wall":
            if not isinstance(command["wall_run_id"], str):
                return _rejected(
                    f"Command {index} wall_run_id must be a string",
                    base_revision_id=base_revision_id,
                )
            if not _is_integer(command["offset_mm"]):
                return _rejected(
                    f"Command {index} offset_mm must be an integer",
                    base_revision_id=base_revision_id,
                )
        elif command_type == "move_opening":
            if not isinstance(command["opening_id"], str):
                return _rejected(
                    f"Command {index} opening_id must be a string",
                    base_revision_id=base_revision_id,
                )
            if not _is_integer(command["station_mm"]):
                return _rejected(
                    f"Command {index} station_mm must be an integer",
                    base_revision_id=base_revision_id,
                )
        normalized_commands.append(dict(command))

    if clarifications:
        if commands:
            return _rejected(
                "Intent cannot contain commands while clarification is unresolved",
                base_revision_id=base_revision_id,
            )
        normalized_clarifications: list[Clarification] = []
        for index, clarification in enumerate(clarifications, start=1):
            if not isinstance(clarification, dict):
                return _rejected(
                    f"Clarification {index} must be an object",
                    base_revision_id=base_revision_id,
                )
            expected_clarification_fields = {"code", "question", "options"}
            if set(clarification) != expected_clarification_fields:
                unknown = sorted(set(clarification) - expected_clarification_fields)
                missing = sorted(expected_clarification_fields - set(clarification))
                details = []
                if unknown:
                    details.append("unknown=" + ",".join(unknown))
                if missing:
                    details.append("missing=" + ",".join(missing))
                return _rejected(
                    f"Clarification {index} fields are invalid: "
                    + "; ".join(details),
                    base_revision_id=base_revision_id,
                )
            code = clarification.get("code")
            question = clarification.get("question")
            options = clarification.get("options")
            if not isinstance(code, str) or not code:
                return _rejected(
                    f"Clarification {index} code must be a non-empty string",
                    base_revision_id=base_revision_id,
                )
            if not isinstance(question, str) or not question:
                return _rejected(
                    f"Clarification {index} question must be a non-empty string",
                    base_revision_id=base_revision_id,
                )
            if not isinstance(options, list) or not all(
                isinstance(option, str) and option for option in options
            ):
                return _rejected(
                    f"Clarification {index} options must be non-empty strings",
                    base_revision_id=base_revision_id,
                )
            normalized_clarifications.append(
                Clarification(
                    code=code,
                    question=question,
                    options=tuple(options),
                )
            )
        return EditIntent(
            status="needs_clarification",
            base_revision_id=base_revision_id,
            clarifications=tuple(normalized_clarifications),
        )
    if not normalized_commands:
        return _rejected(
            "Ready intent must contain at least one command",
            base_revision_id=base_revision_id,
        )
    return EditIntent(
        status="ready",
        base_revision_id=base_revision_id,
        commands=tuple(normalized_commands),
    )


def preview_edit_intent(
    base: PlanRevision,
    intent: EditIntent,
) -> RevisionResult:
    if intent.status != "ready":
        return RevisionResult(
            False,
            base,
            intent.errors or ("Intent is not ready for preview",),
        )
    if intent.base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    return apply_transaction(
        base,
        base_revision_id=base.revision_id,
        commands=intent.commands,
    )
