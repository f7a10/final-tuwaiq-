import json

from dcel_editor import (
    face_area_m2,
    make_two_room_revision,
    opening_segment_mm,
)
from edit_intent_contract import (
    openrouter_request_contract,
    preview_edit_intent,
    validate_edit_intent,
)


def test_valid_model_intent_becomes_safe_preview_without_mutating_source():
    base = make_two_room_revision()
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [
                {
                    "type": "move_opening",
                    "opening_id": "entrance",
                    "station_mm": 2000,
                },
                {
                    "type": "move_wall",
                    "wall_run_id": "shared",
                    "offset_mm": 500,
                },
            ],
            "clarifications": [],
        }
    )

    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )
    preview = preview_edit_intent(base, intent)

    assert intent.status == "ready"
    assert intent.errors == ()
    assert [command["type"] for command in intent.commands] == [
        "move_opening",
        "move_wall",
    ]
    assert preview.accepted is True
    assert preview.revision.parent_id == base.revision_id
    assert face_area_m2(preview.revision, "left") == 13.5
    assert face_area_m2(preview.revision, "right") == 10.5
    entrance_start, entrance_end = opening_segment_mm(
        preview.revision,
        "entrance",
    )
    assert entrance_start == (0, 1550)
    assert entrance_end == (0, 2450)

    assert face_area_m2(base, "left") == 12.0
    assert opening_segment_mm(base, "entrance")[0] == (0, 1050)


def test_duplicate_json_key_is_rejected_before_preview():
    base = make_two_room_revision()
    payload = (
        '{"schema_version":"emad.edit-intent.v1",'
        f'"base_revision_id":"{base.revision_id}",'
        '"commands":[{"type":"move_wall","wall_run_id":"shared",'
        '"offset_mm":500,"offset_mm":3500}],"clarifications":[]}'
    )

    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )
    preview = preview_edit_intent(base, intent)

    assert intent.status == "rejected"
    assert any("duplicate" in error.lower() and "offset_mm" in error for error in intent.errors)
    assert preview.accepted is False
    assert preview.revision is base
    assert face_area_m2(base, "left") == 12.0


def test_unstructured_clarification_entry_is_rejected_cleanly():
    base = make_two_room_revision()
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [],
            "clarifications": ["move right?"],
        }
    )

    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )

    assert intent.status == "rejected"
    assert any("clarification 1" in error.lower() for error in intent.errors)


def test_structured_ambiguity_returns_typed_question_and_blocks_preview():
    base = make_two_room_revision()
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [],
            "clarifications": [
                {
                    "code": "direction_reference",
                    "question": "ما المقصود بالطرف الأيمن؟",
                    "options": ["الطرف أ", "الطرف ب"],
                }
            ],
        }
    )

    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )
    preview = preview_edit_intent(base, intent)

    assert intent.status == "needs_clarification"
    assert len(intent.clarifications) == 1
    clarification = intent.clarifications[0]
    assert clarification.code == "direction_reference"
    assert clarification.question == "ما المقصود بالطرف الأيمن؟"
    assert clarification.options == ("الطرف أ", "الطرف ب")
    assert preview.accepted is False
    assert preview.revision is base


def test_model_cannot_submit_unbounded_command_batch():
    base = make_two_room_revision()
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [
                {
                    "type": "move_wall",
                    "wall_run_id": "shared",
                    "offset_mm": 1,
                }
                for _ in range(21)
            ],
            "clarifications": [],
        }
    )

    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )

    assert intent.status == "rejected"
    assert any("20" in error and "commands" in error for error in intent.errors)


def test_openrouter_request_contract_requires_strict_structured_output():
    base = make_two_room_revision()

    contract = openrouter_request_contract(base.revision_id)

    assert contract["provider"] == {"require_parameters": True}
    response_format = contract["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "emad_edit_intent_v1"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "schema_version",
        "base_revision_id",
        "commands",
        "clarifications",
    }
    assert schema["properties"]["base_revision_id"]["const"] == base.revision_id
    assert schema["properties"]["commands"]["maxItems"] == 20
    assert len(schema["properties"]["commands"]["items"]["anyOf"]) == 2


def test_local_validator_rejects_extra_clarification_fields():
    base = make_two_room_revision()
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [],
            "clarifications": [
                {
                    "code": "direction_reference",
                    "question": "أي طرف تقصد؟",
                    "options": ["أ", "ب"],
                    "suggested_answer": "أ",
                }
            ],
        }
    )

    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )

    assert intent.status == "rejected"
    assert any(
        "suggested_answer" in error and "clarification 1" in error.lower()
        for error in intent.errors
    )


def test_local_validator_allows_only_one_clarification_question():
    base = make_two_room_revision()
    question = {
        "code": "direction_reference",
        "question": "أي طرف تقصد؟",
        "options": ["أ", "ب"],
    }
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [],
            "clarifications": [question, question],
        }
    )

    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )

    assert intent.status == "rejected"
    assert any(
        "one clarification" in error.lower()
        for error in intent.errors
    )
