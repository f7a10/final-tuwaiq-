from __future__ import annotations

from dataclasses import dataclass

from dcel_editor import PlanRevision, RevisionResult, validate_dcel
from deterministic_planner import Candidate
from edit_intent_contract import Clarification, EditIntent, preview_edit_intent


@dataclass(frozen=True)
class SessionActionResult:
    accepted: bool
    revision: PlanRevision
    message_ar: str


@dataclass(frozen=True)
class _HistoryEntry:
    label_ar: str
    before: PlanRevision
    after: PlanRevision


class EditorSession:
    def __init__(
        self,
        revision: PlanRevision,
        *,
        scale_confidence: float,
        geometry_confidence: float,
    ) -> None:
        self.current_revision = revision
        self.scale_confidence = scale_confidence
        self.geometry_confidence = geometry_confidence
        self.state = "browsing"
        self.interaction_count = 0
        self._selection_labels: list[str] = []
        self.preview_revision: PlanRevision | None = None
        self._preview_base_revision_id: str | None = None
        self._pending_operation_label_ar: str | None = None
        self._clarification: Clarification | None = None
        self._blocking_error_ar = ""
        self._undo_stack: list[_HistoryEntry] = []
        self._redo_stack: list[_HistoryEntry] = []

    @property
    def selection_breadcrumb_ar(self) -> tuple[str, ...]:
        return tuple(self._selection_labels)

    @property
    def primary_action_label_ar(self) -> str:
        if self.state == "needs_clarification":
            return "اختر الإجابة"
        if self.state == "preview_stale":
            return "تحديث المعاينة"
        if self.state == "preview_blocked":
            return "راجع القيمة"
        if self.state == "preview_preliminary":
            if self.scale_confidence < 0.8:
                return "معايرة المقياس للمتابعة"
            return "تأكيد الرسم للمتابعة"
        if self.state != "preview_ready":
            return "إنشاء معاينة"
        return "اعتماد التعديل"

    @property
    def confidence_badge_ar(self) -> str:
        if self.scale_confidence < 0.8 or self.geometry_confidence < 0.8:
            return "تقريبي"
        return "مؤكد"

    @property
    def can_approve(self) -> bool:
        return self.state == "preview_ready"

    @property
    def blocking_error_ar(self) -> str:
        return self._blocking_error_ar

    @property
    def clarification_question_ar(self) -> str | None:
        if self._clarification is None:
            return None
        return self._clarification.question

    @property
    def clarification_options_ar(self) -> tuple[str, ...]:
        if self._clarification is None:
            return ()
        return self._clarification.options

    @property
    def undo_label_ar(self) -> str | None:
        if not self._undo_stack:
            return None
        return f"تراجع عن {self._undo_stack[-1].label_ar}"

    @property
    def redo_label_ar(self) -> str | None:
        if not self._redo_stack:
            return None
        return f"إعادة {self._redo_stack[-1].label_ar}"

    @property
    def history_position(self) -> tuple[int, int]:
        applied = len(self._undo_stack)
        return applied, applied + len(self._redo_stack)

    def select_room(self, room_id: str, *, label_ar: str) -> None:
        room_ids = {
            face.id for face in self.current_revision.faces if face.kind == "room"
        }
        if room_id not in room_ids:
            raise ValueError(f"Unknown room: {room_id}")
        self._selection_labels = [label_ar]
        self.interaction_count += 1
        self.state = "selected"

    def select_wall(self, wall_run_id: str, *, label_ar: str) -> None:
        if wall_run_id not in {run.id for run in self.current_revision.wall_runs}:
            raise ValueError(f"Unknown wall run: {wall_run_id}")
        self._selection_labels = self._selection_labels[:1] + [label_ar]
        self.interaction_count += 1
        self.state = "selected"

    def select_opening(self, opening_id: str, *, label_ar: str) -> None:
        if opening_id not in {
            opening.id for opening in self.current_revision.openings
        }:
            raise ValueError(f"Unknown opening: {opening_id}")
        self._selection_labels = self._selection_labels[:2] + [label_ar]
        self.interaction_count += 1
        self.state = "selected"

    def submit_intent(
        self,
        intent: EditIntent,
        *,
        operation_label_ar: str,
    ) -> RevisionResult:
        self.interaction_count += 1
        result = preview_edit_intent(self.current_revision, intent)
        if not result.accepted:
            self.preview_revision = None
            self._preview_base_revision_id = None
            self._pending_operation_label_ar = None
            self.state = (
                "needs_clarification"
                if intent.status == "needs_clarification"
                else "preview_blocked"
            )
            self._clarification = (
                intent.clarifications[0]
                if intent.status == "needs_clarification"
                and intent.clarifications
                else None
            )
            if intent.status != "needs_clarification":
                selected_element = (
                    self._selection_labels[-1]
                    if self._selection_labels
                    else "العنصر المحدد"
                )
                self._blocking_error_ar = (
                    f"{selected_element}: مقدار الحركة غير مسموح لأنه ينتج "
                    "شكلاً غير صالح. قلل القيمة ثم أنشئ المعاينة من جديد."
                )
            return result
        self._clarification = None
        self._blocking_error_ar = ""
        self.preview_revision = result.revision
        self._preview_base_revision_id = self.current_revision.revision_id
        self._pending_operation_label_ar = operation_label_ar
        self.state = (
            "preview_preliminary"
            if self.scale_confidence < 0.8 or self.geometry_confidence < 0.8
            else "preview_ready"
        )
        return result

    def preview_planner_candidate(
        self,
        candidate: Candidate,
        *,
        operation_label_ar: str,
    ) -> RevisionResult:
        self.interaction_count += 1
        errors: list[str] = []
        if candidate.plan.parent_id != self.current_revision.revision_id:
            errors.append("اقتراح المخطط مبني على نسخة قديمة")
        if candidate.hard_violation_count != 0:
            errors.append("اقتراح المخطط يحتوي على أخطاء مانعة")
        errors.extend(validate_dcel(candidate.plan))
        if errors:
            self.preview_revision = None
            self._preview_base_revision_id = None
            self._pending_operation_label_ar = None
            self._blocking_error_ar = (
                "تعذر استخدام هذا الاقتراح. اختر اقتراحاً آخر أو أعد إنشاءه."
            )
            self.state = "preview_blocked"
            return RevisionResult(False, self.current_revision, tuple(errors))
        self._clarification = None
        self._blocking_error_ar = ""
        self.preview_revision = candidate.plan
        self._preview_base_revision_id = self.current_revision.revision_id
        self._pending_operation_label_ar = operation_label_ar
        self.state = (
            "preview_preliminary"
            if self.scale_confidence < 0.8 or self.geometry_confidence < 0.8
            else "preview_ready"
        )
        return RevisionResult(True, candidate.plan, ())

    def mark_draft_changed(self) -> None:
        self.interaction_count += 1
        if self.preview_revision is not None:
            self.state = "preview_stale"
        else:
            self.state = "draft_changed"

    def approve_preview(self) -> SessionActionResult:
        self.interaction_count += 1
        if self.state == "preview_preliminary":
            message = (
                "يجب معايرة المقياس قبل اعتماد تعديل متري"
                if self.scale_confidence < 0.8
                else "يجب تأكيد الرسم قبل اعتماد التعديل"
            )
            return SessionActionResult(False, self.current_revision, message)
        if self.state == "preview_stale":
            return SessionActionResult(
                False,
                self.current_revision,
                "المعاينة قديمة وتحتاج إلى تحديث",
            )
        if (
            self.state != "preview_ready"
            or self.preview_revision is None
            or self._pending_operation_label_ar is None
        ):
            return SessionActionResult(
                False,
                self.current_revision,
                "لا توجد معاينة صالحة للاعتماد",
            )
        if self._preview_base_revision_id != self.current_revision.revision_id:
            self.state = "preview_stale"
            return SessionActionResult(
                False,
                self.current_revision,
                "المعاينة قديمة وتحتاج إلى تحديث",
            )
        entry = _HistoryEntry(
            label_ar=self._pending_operation_label_ar,
            before=self.current_revision,
            after=self.preview_revision,
        )
        self.current_revision = self.preview_revision
        self._undo_stack.append(entry)
        self._redo_stack.clear()
        self.preview_revision = None
        self._preview_base_revision_id = None
        self._pending_operation_label_ar = None
        self.state = "committed"
        return SessionActionResult(
            True,
            self.current_revision,
            "تم اعتماد التعديل",
        )

    def undo(self) -> SessionActionResult:
        if not self._undo_stack:
            return SessionActionResult(
                False,
                self.current_revision,
                "لا يوجد تعديل للتراجع عنه",
            )
        entry = self._undo_stack.pop()
        self.current_revision = entry.before
        self._redo_stack.append(entry)
        self.state = "committed"
        return SessionActionResult(
            True,
            self.current_revision,
            f"تم التراجع عن {entry.label_ar}",
        )

    def redo(self) -> SessionActionResult:
        if not self._redo_stack:
            return SessionActionResult(
                False,
                self.current_revision,
                "لا يوجد تعديل لإعادته",
            )
        entry = self._redo_stack.pop()
        self.current_revision = entry.after
        self._undo_stack.append(entry)
        self.state = "committed"
        return SessionActionResult(
            True,
            self.current_revision,
            f"تمت إعادة {entry.label_ar}",
        )
