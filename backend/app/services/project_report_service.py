from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.database import EditorRevision, EditorSession, Project


class ProjectReportError(RuntimeError):
    """Raised when a project has no approved editor revision to report."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _analysis_rooms(project: Project) -> list[dict[str, Any]]:
    if not project.rooms_data:
        return []
    try:
        value = json.loads(project.rooms_data)
    except (json.JSONDecodeError, TypeError):
        return []
    return value if isinstance(value, list) else []


def build_project_report(db: Session, project: Project) -> dict[str, Any]:
    session = db.query(EditorSession).filter(EditorSession.project_id == project.id).first()
    if session is None:
        raise ProjectReportError("editor_session_not_ready")
    revision = db.get(EditorRevision, session.current_revision_id)
    if revision is None:
        raise ProjectReportError("current_revision_missing")

    geometry = json.loads(revision.geometry_json)
    rooms = [
        {
            "id": room["id"],
            "label": room.get("label") or room["id"],
            "width_m": round(float(room["width_mm"]) / 1000, 2),
            "height_m": round(float(room["height_mm"]) / 1000, 2),
            "area_m2": round(float(room["area_m2"]), 2),
        }
        for room in geometry.get("rooms", [])
    ]
    findings = []
    for room in _analysis_rooms(project):
        if room.get("isCompliant") is False:
            findings.append({
                "room_id": str(room.get("id") or ""),
                "label": str(room.get("type") or "عنصر غير مصنف"),
                "status_ar": "مشكلة محتملة",
                "reason_ar": room.get("ragReason") or "تحتاج القيمة المرصودة إلى مراجعة مختص.",
                "reference": room.get("reference") or "المصدر غير موثق — يحتاج مراجعة مختص",
            })

    return {
        "schema_version": "emad.project-report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "id": project.id,
            "title": project.title or f"مشروع #{project.id}",
            "status": project.status,
            "created_at": _iso(project.created_at),
        },
        "revision": {
            "id": revision.revision_hash,
            "number": revision.revision_number,
            "label": revision.label_ar or "نسخة معتمدة",
            "created_at": _iso(revision.created_at),
        },
        "confidence": {
            "scale": session.scale_confidence,
            "geometry": session.geometry_confidence,
        },
        "summary": {
            "rooms_count": len(rooms),
            "total_area_m2": round(sum(room["area_m2"] for room in rooms), 2),
            "potential_issues_count": len(findings),
            "compliance_score": project.compliance_score,
        },
        "rooms": rooms,
        "findings": findings,
        "disclaimer_ar": (
            "هذا التقرير مراجعة أولية مولدة آليًا لنسخة العرض، وليس اعتمادًا هندسيًا أو إنشائيًا. "
            "تبقى القياسات والحالة الإنشائية ومتطلبات الكود بحاجة إلى تحقق مختص قبل التنفيذ."
        ),
    }
