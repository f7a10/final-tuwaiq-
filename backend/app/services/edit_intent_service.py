from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from backend.app.services.ai_provider import OpenRouterProvider


class EditIntentError(RuntimeError):
    """Raised when an AI edit plan is invalid or unsafe to preview."""


@dataclass(frozen=True)
class EditSelection:
    room_id: str
    element_id: str
    element_type: str


EDIT_INTENT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "emad_edit_intent",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["ready", "needs_clarification", "unsupported"],
                },
                "operation": {
                    "anyOf": [
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "kind": {"type": "string", "enum": ["move_wall"]},
                                "target_id": {"type": "string"},
                                "delta_cm": {"type": "number", "minimum": -150, "maximum": 150},
                            },
                            "required": ["kind", "target_id", "delta_cm"],
                        },
                        {"type": "null"},
                    ]
                },
                "explanation": {"type": "string"},
                "clarification": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "warnings": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            },
            "required": ["status", "operation", "explanation", "clarification", "warnings"],
        },
    },
}


class EditIntentService:
    def __init__(self, provider: OpenRouterProvider) -> None:
        self.provider = provider

    def plan(self, *, prompt: str, selection: EditSelection) -> dict[str, Any]:
        response = self.provider.complete_text(
            role="planning",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت مفسر طلبات تعديل لمخطط سكني. أعد نية تعديل typed فقط. "
                        "لا تنشئ إحداثيات، لا تدّعي أن جدارًا إنشائيًا قابل للإزالة، ولا تعتمد أي تغيير. "
                        "العملية المدعومة حاليًا هي move_wall على العنصر المحدد فقط وبحد أقصى 150 سم. "
                        "إذا غاب الاتجاه أو المقدار أو كان الطلب خارج العملية المدعومة، اطلب توضيحًا أو أعد unsupported."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": prompt,
                            "selection": {
                                "room_id": selection.room_id,
                                "element_id": selection.element_id,
                                "element_type": selection.element_type,
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0,
            max_tokens=500,
            response_format=EDIT_INTENT_SCHEMA,
            extra_body={"provider": {"require_parameters": True}},
        )
        try:
            payload = json.loads(response)
        except (TypeError, json.JSONDecodeError) as error:
            raise EditIntentError("OpenRouter returned invalid structured edit intent") from error

        status = payload.get("status")
        if status not in {"ready", "needs_clarification", "unsupported"}:
            raise EditIntentError("Edit intent status is invalid")

        operation = payload.get("operation")
        if status != "ready":
            return {
                "status": status,
                "operation": None,
                "explanation": str(payload.get("explanation") or ""),
                "clarification": payload.get("clarification"),
                "warnings": list(payload.get("warnings") or []),
            }

        if selection.element_type != "wall" or not isinstance(operation, dict):
            raise EditIntentError("Ready intent requires a selected wall operation")
        if operation.get("kind") != "move_wall":
            raise EditIntentError("Unsupported edit operation")
        if operation.get("target_id") != selection.element_id:
            raise EditIntentError("AI operation target does not match the selected element")

        try:
            delta_cm = float(operation["delta_cm"])
        except (KeyError, TypeError, ValueError) as error:
            raise EditIntentError("Wall movement must include a numeric delta_cm") from error
        if delta_cm == 0 or not -150 <= delta_cm <= 150:
            raise EditIntentError("Wall movement is outside the allowed preview range")

        return {
            "status": "ready",
            "operation": {
                "kind": "move_wall",
                "target_id": selection.element_id,
                "delta_cm": delta_cm,
            },
            "explanation": str(payload.get("explanation") or ""),
            "clarification": None,
            "warnings": list(payload.get("warnings") or []),
        }
