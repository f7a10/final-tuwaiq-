import json

from dcel_editor import face_area_m2, make_two_room_revision
from edit_intent_contract import validate_edit_intent
from deterministic_planner import PlannerRequest, generate_repair_candidates
from editor_session import EditorSession


def test_homeowner_can_preview_approve_undo_and_redo_one_named_change():
    base = make_two_room_revision()
    session = EditorSession(
        base,
        scale_confidence=0.96,
        geometry_confidence=0.95,
    )
    session.select_room("left", label_ar="غرفة المعيشة")
    session.select_wall("shared", label_ar="الجدار المشترك")
    session.select_opening("entrance", label_ar="الباب الرئيسي")
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

    preview = session.submit_intent(
        intent,
        operation_label_ar="نقل الباب وتوسيع غرفة المعيشة",
    )

    assert preview.accepted is True
    assert session.state == "preview_ready"
    assert session.current_revision is base
    assert session.preview_revision is not base
    assert session.selection_breadcrumb_ar == (
        "غرفة المعيشة",
        "الجدار المشترك",
        "الباب الرئيسي",
    )
    assert session.primary_action_label_ar == "اعتماد التعديل"
    assert session.interaction_count == 4

    approved = session.approve_preview()

    assert approved.accepted is True
    assert session.state == "committed"
    assert session.current_revision is preview.revision
    assert face_area_m2(session.current_revision, "left") == 13.5
    assert session.undo_label_ar == "تراجع عن نقل الباب وتوسيع غرفة المعيشة"
    assert session.interaction_count == 5

    undone = session.undo()

    assert undone.accepted is True
    assert session.current_revision is base
    assert session.redo_label_ar == "إعادة نقل الباب وتوسيع غرفة المعيشة"

    redone = session.redo()

    assert redone.accepted is True
    assert session.current_revision is preview.revision
    assert face_area_m2(session.current_revision, "left") == 13.5


def test_changed_draft_marks_preview_stale_and_blocks_approval():
    base = make_two_room_revision()
    session = EditorSession(
        base,
        scale_confidence=0.96,
        geometry_confidence=0.95,
    )
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [
                {
                    "type": "move_wall",
                    "wall_run_id": "shared",
                    "offset_mm": 500,
                }
            ],
            "clarifications": [],
        }
    )
    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )
    preview = session.submit_intent(
        intent,
        operation_label_ar="توسيع غرفة المعيشة",
    )

    session.mark_draft_changed()
    approval = session.approve_preview()

    assert preview.accepted is True
    assert session.state == "preview_stale"
    assert session.preview_revision is preview.revision
    assert session.primary_action_label_ar == "تحديث المعاينة"
    assert approval.accepted is False
    assert approval.revision is base
    assert "قديمة" in approval.message_ar
    assert session.current_revision is base


def test_ambiguous_request_shows_one_question_without_creating_preview():
    base = make_two_room_revision()
    session = EditorSession(
        base,
        scale_confidence=0.96,
        geometry_confidence=0.95,
    )
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [],
            "clarifications": [
                {
                    "code": "direction_reference",
                    "question": "إلى أي طرف تريد تحريك النافذة؟",
                    "options": ["الطرف أ", "الطرف ب"],
                }
            ],
        }
    )
    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )

    result = session.submit_intent(
        intent,
        operation_label_ar="تحريك النافذة",
    )

    assert result.accepted is False
    assert session.state == "needs_clarification"
    assert session.clarification_question_ar == (
        "إلى أي طرف تريد تحريك النافذة؟"
    )
    assert session.clarification_options_ar == ("الطرف أ", "الطرف ب")
    assert session.primary_action_label_ar == "اختر الإجابة"
    assert session.preview_revision is None
    assert session.current_revision is base


def test_low_scale_confidence_allows_preview_but_blocks_metric_approval():
    base = make_two_room_revision()
    session = EditorSession(
        base,
        scale_confidence=0.52,
        geometry_confidence=0.95,
    )
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [
                {
                    "type": "move_wall",
                    "wall_run_id": "shared",
                    "offset_mm": 500,
                }
            ],
            "clarifications": [],
        }
    )
    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )

    preview = session.submit_intent(
        intent,
        operation_label_ar="توسيع غرفة المعيشة",
    )
    approval = session.approve_preview()

    assert preview.accepted is True
    assert session.state == "preview_preliminary"
    assert session.confidence_badge_ar == "تقريبي"
    assert session.primary_action_label_ar == "معايرة المقياس للمتابعة"
    assert session.can_approve is False
    assert approval.accepted is False
    assert approval.revision is base
    assert "معايرة" in approval.message_ar
    assert session.preview_revision is preview.revision
    assert session.current_revision is base


def test_planner_candidate_uses_same_preview_approval_and_undo_path():
    base = make_two_room_revision()
    request = PlannerRequest(
        wall_run_id="shared",
        offsets_mm=(1500, 500, 1000),
        hard_min_area_m2=(("left", 13.0), ("right", 7.0)),
        target_area_m2=(("left", 15.0), ("right", 9.0)),
        priority_face_id="left",
        ruleset_version="rules-spike-v1",
        engine_version="planner-spike-v1",
        seed=17,
        search_budget=20,
    )
    planner_result = generate_repair_candidates(base, request)
    balanced = next(
        candidate
        for candidate in planner_result.candidates
        if candidate.profile == "balanced"
    )
    session = EditorSession(
        base,
        scale_confidence=0.96,
        geometry_confidence=0.95,
    )

    preview = session.preview_planner_candidate(
        balanced,
        operation_label_ar="تطبيق التحسين المتوازن",
    )

    assert preview.accepted is True
    assert session.state == "preview_ready"
    assert session.current_revision is base
    assert session.preview_revision is balanced.plan
    assert session.primary_action_label_ar == "اعتماد التعديل"

    approved = session.approve_preview()
    undone = session.undo()

    assert approved.accepted is True
    assert undone.accepted is True
    assert session.current_revision is base
    assert session.redo_label_ar == "إعادة تطبيق التحسين المتوازن"


def test_impossible_geometry_names_selected_element_and_recovery_action():
    base = make_two_room_revision()
    session = EditorSession(
        base,
        scale_confidence=0.96,
        geometry_confidence=0.95,
    )
    session.select_room("right", label_ar="غرفة النوم")
    session.select_wall("shared", label_ar="الجدار المشترك")
    payload = json.dumps(
        {
            "schema_version": "emad.edit-intent.v1",
            "base_revision_id": base.revision_id,
            "commands": [
                {
                    "type": "move_wall",
                    "wall_run_id": "shared",
                    "offset_mm": 5000,
                }
            ],
            "clarifications": [],
        }
    )
    intent = validate_edit_intent(
        payload,
        current_revision_id=base.revision_id,
    )

    preview = session.submit_intent(
        intent,
        operation_label_ar="توسيع غرفة النوم",
    )
    approval = session.approve_preview()

    assert preview.accepted is False
    assert session.state == "preview_blocked"
    assert session.primary_action_label_ar == "راجع القيمة"
    assert "الجدار المشترك" in session.blocking_error_ar
    assert "قلل" in session.blocking_error_ar
    assert "المعاينة" in session.blocking_error_ar
    assert session.preview_revision is None
    assert approval.accepted is False
    assert session.current_revision is base


def test_ten_commits_can_be_undone_and_redone_without_history_drift():
    base = make_two_room_revision()
    session = EditorSession(
        base,
        scale_confidence=0.96,
        geometry_confidence=0.95,
    )
    committed_revision_ids = []
    for step in range(1, 11):
        payload = json.dumps(
            {
                "schema_version": "emad.edit-intent.v1",
                "base_revision_id": session.current_revision.revision_id,
                "commands": [
                    {
                        "type": "move_wall",
                        "wall_run_id": "shared",
                        "offset_mm": 100,
                    }
                ],
                "clarifications": [],
            }
        )
        intent = validate_edit_intent(
            payload,
            current_revision_id=session.current_revision.revision_id,
        )
        preview = session.submit_intent(
            intent,
            operation_label_ar=f"توسيع تدريجي {step}",
        )
        approved = session.approve_preview()
        assert preview.accepted is True
        assert approved.accepted is True
        committed_revision_ids.append(session.current_revision.revision_id)

    final_revision = session.current_revision
    assert session.history_position == (10, 10)
    assert len(set(committed_revision_ids)) == 10

    for _ in range(10):
        assert session.undo().accepted is True

    assert session.current_revision is base
    assert session.history_position == (0, 10)

    for _ in range(10):
        assert session.redo().accepted is True

    assert session.current_revision is final_revision
    assert session.history_position == (10, 10)
    assert face_area_m2(session.current_revision, "left") == 15.0
