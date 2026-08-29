from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.database import (
    EditorPreview,
    EditorRevision,
    EditorSession,
    Project,
)
from backend.app.services.rect_editor import GeometryError, build_geometry, preview_move_wall


class EditorSessionError(RuntimeError):
    """Raised when a persisted editor transition is invalid or unsafe."""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _revision_hash(*, parent_hash: str | None, geometry: dict[str, Any]) -> str:
    payload = {"parent_hash": parent_hash, "geometry": geometry}
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


class EditorSessionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def initialize(
        self,
        *,
        project: Project,
        scale_confidence: float,
        geometry_confidence: float,
    ) -> dict[str, Any]:
        existing = self.db.query(EditorSession).filter(
            EditorSession.project_id == project.id
        ).first()
        if existing:
            return self.get_state(project.id)
        if project.status != "completed" or not project.rooms_data:
            raise EditorSessionError("project_analysis_not_ready")

        try:
            rooms_data = json.loads(project.rooms_data)
            geometry = build_geometry(
                rooms_data,
                scale_confidence=scale_confidence,
                geometry_confidence=geometry_confidence,
            )
        except (json.JSONDecodeError, GeometryError, TypeError) as error:
            raise EditorSessionError("project_geometry_unavailable") from error

        revision = EditorRevision(
            project_id=project.id,
            revision_number=0,
            revision_hash=_revision_hash(parent_hash=None, geometry=geometry),
            parent_revision_id=None,
            geometry_json=_json(geometry),
            operation_json=None,
            label_ar="المخطط بعد التحليل",
        )
        self.db.add(revision)
        self.db.flush()
        session = EditorSession(
            project_id=project.id,
            current_revision_id=revision.id,
            redo_stack_json="[]",
            scale_confidence=float(scale_confidence),
            geometry_confidence=float(geometry_confidence),
        )
        self.db.add(session)
        self.db.commit()
        return self.get_state(project.id)

    def get_state(self, project_id: int) -> dict[str, Any]:
        session = self._session(project_id)
        revision = self.db.get(EditorRevision, session.current_revision_id)
        if revision is None:
            raise EditorSessionError("current_revision_missing")
        redo_stack = self._redo_stack(session)
        pending = self.db.query(EditorPreview).filter(
            EditorPreview.project_id == project_id,
            EditorPreview.status == "pending",
        ).order_by(EditorPreview.id.desc()).first()
        return {
            "project_id": project_id,
            "revision_id": revision.revision_hash,
            "revision_number": revision.revision_number,
            "geometry": json.loads(revision.geometry_json),
            "scale_confidence": session.scale_confidence,
            "geometry_confidence": session.geometry_confidence,
            "can_undo": revision.parent_revision_id is not None,
            "can_redo": bool(redo_stack),
            "pending_preview": self._preview_payload(pending) if pending else None,
        }

    def confirm_draft(
        self,
        *,
        project_id: int,
        scale_confirmed: bool,
        geometry_confirmed: bool,
    ) -> dict[str, Any]:
        if not scale_confirmed or not geometry_confirmed:
            raise EditorSessionError("draft_confirmation_incomplete")
        session = self._session(project_id)
        session.scale_confidence = 1.0
        session.geometry_confidence = 1.0
        self.db.commit()
        return self.get_state(project_id)

    def create_preview(
        self,
        *,
        project_id: int,
        base_revision_id: str,
        wall_id: str,
        offset_mm: int,
        label_ar: str,
    ) -> dict[str, Any]:
        session = self._session(project_id)
        current = self.db.get(EditorRevision, session.current_revision_id)
        if current is None or current.revision_hash != base_revision_id:
            raise EditorSessionError("stale_base_revision")
        try:
            geometry = preview_move_wall(
                json.loads(current.geometry_json),
                wall_id=wall_id,
                offset_mm=offset_mm,
            )
        except GeometryError as error:
            raise EditorSessionError("unsafe_geometry_operation") from error

        self._invalidate_pending(project_id)
        operation = {
            "kind": "move_wall",
            "wall_id": wall_id,
            "offset_mm": offset_mm,
        }
        preview = EditorPreview(
            project_id=project_id,
            base_revision_id=current.id,
            geometry_json=_json(geometry),
            operation_json=_json(operation),
            label_ar=label_ar,
            status="pending",
        )
        self.db.add(preview)
        self.db.commit()
        self.db.refresh(preview)
        return self._preview_payload(preview)

    def approve_preview(
        self,
        *,
        project_id: int,
        preview_id: int,
        structural_review_confirmed: bool,
    ) -> dict[str, Any]:
        session = self._session(project_id)
        preview = self.db.query(EditorPreview).filter(
            EditorPreview.id == preview_id,
            EditorPreview.project_id == project_id,
        ).first()
        if preview is None or preview.status != "pending":
            raise EditorSessionError("preview_not_available")
        if preview.base_revision_id != session.current_revision_id:
            preview.status = "stale"
            self.db.commit()
            raise EditorSessionError("stale_preview")
        if session.scale_confidence < 0.8:
            raise EditorSessionError("scale_calibration_required")
        if session.geometry_confidence < 0.8:
            raise EditorSessionError("geometry_confirmation_required")

        current = self.db.get(EditorRevision, session.current_revision_id)
        operation = json.loads(preview.operation_json)
        current_geometry = json.loads(current.geometry_json)
        wall = next(
            (item for item in current_geometry["walls"] if item["id"] == operation["wall_id"]),
            None,
        )
        if wall is None:
            raise EditorSessionError("preview_wall_missing")
        if wall.get("structural_status") == "unknown" and not structural_review_confirmed:
            raise EditorSessionError("structural_review_required")

        latest = self.db.query(EditorRevision).filter(
            EditorRevision.project_id == project_id
        ).order_by(EditorRevision.revision_number.desc()).first()
        geometry = json.loads(preview.geometry_json)
        revision = EditorRevision(
            project_id=project_id,
            revision_number=(latest.revision_number + 1 if latest else 1),
            revision_hash=_revision_hash(
                parent_hash=current.revision_hash,
                geometry=geometry,
            ),
            parent_revision_id=current.id,
            geometry_json=preview.geometry_json,
            operation_json=_json({
                **operation,
                "structural_review_confirmed": structural_review_confirmed,
            }),
            label_ar=preview.label_ar,
        )
        self.db.add(revision)
        self.db.flush()
        session.current_revision_id = revision.id
        session.redo_stack_json = "[]"
        preview.status = "approved"
        self.db.commit()
        return self.get_state(project_id)

    def discard_preview(self, *, project_id: int, preview_id: int) -> dict[str, Any]:
        preview = self.db.query(EditorPreview).filter(
            EditorPreview.id == preview_id,
            EditorPreview.project_id == project_id,
            EditorPreview.status == "pending",
        ).first()
        if preview is None:
            raise EditorSessionError("preview_not_available")
        preview.status = "discarded"
        self.db.commit()
        return self.get_state(project_id)

    def undo(self, project_id: int) -> dict[str, Any]:
        session = self._session(project_id)
        current = self.db.get(EditorRevision, session.current_revision_id)
        if current is None or current.parent_revision_id is None:
            raise EditorSessionError("nothing_to_undo")
        redo_stack = self._redo_stack(session)
        redo_stack.append(current.id)
        session.current_revision_id = current.parent_revision_id
        session.redo_stack_json = _json(redo_stack)
        self._invalidate_pending(project_id)
        self.db.commit()
        return self.get_state(project_id)

    def redo(self, project_id: int) -> dict[str, Any]:
        session = self._session(project_id)
        redo_stack = self._redo_stack(session)
        if not redo_stack:
            raise EditorSessionError("nothing_to_redo")
        target_id = redo_stack.pop()
        target = self.db.get(EditorRevision, target_id)
        if target is None or target.parent_revision_id != session.current_revision_id:
            session.redo_stack_json = "[]"
            self.db.commit()
            raise EditorSessionError("redo_branch_invalid")
        session.current_revision_id = target.id
        session.redo_stack_json = _json(redo_stack)
        self._invalidate_pending(project_id)
        self.db.commit()
        return self.get_state(project_id)

    def _session(self, project_id: int) -> EditorSession:
        session = self.db.query(EditorSession).filter(
            EditorSession.project_id == project_id
        ).first()
        if session is None:
            raise EditorSessionError("editor_session_not_initialized")
        return session

    @staticmethod
    def _redo_stack(session: EditorSession) -> list[int]:
        try:
            values = json.loads(session.redo_stack_json or "[]")
            return [int(value) for value in values]
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise EditorSessionError("redo_history_corrupt") from error

    def _invalidate_pending(self, project_id: int) -> None:
        previews = self.db.query(EditorPreview).filter(
            EditorPreview.project_id == project_id,
            EditorPreview.status == "pending",
        ).all()
        for preview in previews:
            preview.status = "stale"

    def _preview_payload(self, preview: EditorPreview) -> dict[str, Any]:
        base = self.db.get(EditorRevision, preview.base_revision_id)
        return {
            "preview_id": preview.id,
            "status": preview.status,
            "base_revision_id": base.revision_hash if base else None,
            "geometry": json.loads(preview.geometry_json),
            "operation": json.loads(preview.operation_json),
            "label_ar": preview.label_ar,
        }
