from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app import config
from backend.app.auth.dependencies import require_auth
from backend.app.models.database import Project, User, get_db
from backend.app.services.ai_provider import (
    OpenRouterProvider,
    ProviderAuthenticationError,
    ProviderCallError,
    ProviderConfigurationError,
    ProviderModels,
)
from backend.app.services.edit_intent_service import (
    EditIntentError,
    EditIntentService,
    EditSelection,
)
from backend.app.services.editor_session_service import (
    EditorSessionError,
    EditorSessionService,
)
from backend.app.services.project_report_service import ProjectReportError, build_project_report

router = APIRouter(prefix="/api", tags=["editor"])


class EditSelectionRequest(BaseModel):
    room_id: str = Field(min_length=1, max_length=100)
    element_id: str = Field(min_length=1, max_length=100)
    element_type: str = Field(min_length=1, max_length=30)


class EditIntentRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    selection: EditSelectionRequest
    revision: int = Field(ge=0)


class EditorPreviewRequest(BaseModel):
    base_revision_id: str = Field(min_length=64, max_length=64)
    wall_id: str = Field(min_length=1, max_length=255)
    offset_mm: int = Field(ge=-1500, le=1500)
    label_ar: str = Field(min_length=1, max_length=255)


class EditorApprovalRequest(BaseModel):
    structural_review_confirmed: bool = False


class EditorDraftConfirmationRequest(BaseModel):
    scale_confirmed: bool
    geometry_confirmed: bool


def get_edit_intent_service() -> EditIntentService:
    provider = OpenRouterProvider(
        api_key=config.OPENROUTER_API_KEY,
        models=ProviderModels(
            vision=config.OPENROUTER_VISION_MODEL,
            planning=config.OPENROUTER_PLANNING_MODEL,
            assistant=config.OPENROUTER_ASSISTANT_MODEL,
            fallbacks=config.OPENROUTER_FALLBACK_MODELS,
        ),
    )
    return EditIntentService(provider)


def get_editor_session_service(db: Session = Depends(get_db)) -> EditorSessionService:
    return EditorSessionService(db)


def _owned_project(db: Session, project_id: int, user_id: int) -> Project:
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user_id,
    ).first()
    if project is None:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    return project


def _raise_editor_http_error(error: EditorSessionError) -> None:
    code = str(error)
    conflict_codes = {
        "stale_base_revision",
        "stale_preview",
        "preview_not_available",
        "nothing_to_undo",
        "nothing_to_redo",
        "redo_branch_invalid",
    }
    status_code = 409 if code in conflict_codes else 422
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": "تعذر تنفيذ انتقال المحرر بأمان."},
    ) from error


@router.post("/projects/{project_id}/edit-intent")
async def plan_edit_intent(
    project_id: int,
    request: EditIntentRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    service: EditIntentService = Depends(get_edit_intent_service),
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")

    try:
        result = service.plan(
            prompt=request.prompt,
            selection=EditSelection(
                room_id=request.selection.room_id,
                element_id=request.selection.element_id,
                element_type=request.selection.element_type,
            ),
        )
    except ProviderConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ai_not_configured",
                "message": "خدمة الذكاء الاصطناعي غير مهيأة حاليًا.",
            },
        ) from error
    except ProviderAuthenticationError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ai_auth_failed",
                "message": "تعذر اعتماد إعدادات مزود الذكاء الاصطناعي.",
            },
        ) from error
    except ProviderCallError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "ai_provider_failed",
                "message": "تعذر الحصول على استجابة صالحة من مزود الذكاء الاصطناعي.",
            },
        ) from error
    except EditIntentError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_edit_intent",
                "message": "أعاد الذكاء الاصطناعي خطة تعديل غير آمنة أو غير صالحة.",
            },
        ) from error

    return {**result, "base_revision": request.revision}


@router.get("/projects/{project_id}/report")
async def get_project_report(
    project_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    project = _owned_project(db, project_id, user.id)
    try:
        return build_project_report(db, project)
    except ProjectReportError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": str(error), "message": "التقرير غير جاهز حتى تتوفر نسخة محرر معتمدة."},
        ) from error


@router.get("/projects/{project_id}/editor")
async def get_editor_state(
    project_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    service: EditorSessionService = Depends(get_editor_session_service),
):
    project = _owned_project(db, project_id, user.id)
    try:
        return service.get_state(project_id)
    except EditorSessionError as error:
        if str(error) != "editor_session_not_initialized":
            _raise_editor_http_error(error)
        try:
            return service.initialize(
                project=project,
                scale_confidence=0.45,
                geometry_confidence=0.65,
            )
        except EditorSessionError as initialization_error:
            _raise_editor_http_error(initialization_error)


@router.post("/projects/{project_id}/editor/previews")
async def create_editor_preview(
    project_id: int,
    request: EditorPreviewRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    service: EditorSessionService = Depends(get_editor_session_service),
):
    _owned_project(db, project_id, user.id)
    try:
        return service.create_preview(
            project_id=project_id,
            base_revision_id=request.base_revision_id,
            wall_id=request.wall_id,
            offset_mm=request.offset_mm,
            label_ar=request.label_ar,
        )
    except EditorSessionError as error:
        _raise_editor_http_error(error)


@router.post("/projects/{project_id}/editor/confirm")
async def confirm_editor_draft(
    project_id: int,
    request: EditorDraftConfirmationRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    service: EditorSessionService = Depends(get_editor_session_service),
):
    _owned_project(db, project_id, user.id)
    try:
        return service.confirm_draft(
            project_id=project_id,
            scale_confirmed=request.scale_confirmed,
            geometry_confirmed=request.geometry_confirmed,
        )
    except EditorSessionError as error:
        _raise_editor_http_error(error)


@router.post("/projects/{project_id}/editor/previews/{preview_id}/approve")
async def approve_editor_preview(
    project_id: int,
    preview_id: int,
    request: EditorApprovalRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    service: EditorSessionService = Depends(get_editor_session_service),
):
    _owned_project(db, project_id, user.id)
    try:
        return service.approve_preview(
            project_id=project_id,
            preview_id=preview_id,
            structural_review_confirmed=request.structural_review_confirmed,
        )
    except EditorSessionError as error:
        _raise_editor_http_error(error)


@router.post("/projects/{project_id}/editor/previews/{preview_id}/discard")
async def discard_editor_preview(
    project_id: int,
    preview_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    service: EditorSessionService = Depends(get_editor_session_service),
):
    _owned_project(db, project_id, user.id)
    try:
        return service.discard_preview(project_id=project_id, preview_id=preview_id)
    except EditorSessionError as error:
        _raise_editor_http_error(error)


@router.post("/projects/{project_id}/editor/undo")
async def undo_editor_revision(
    project_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    service: EditorSessionService = Depends(get_editor_session_service),
):
    _owned_project(db, project_id, user.id)
    try:
        return service.undo(project_id)
    except EditorSessionError as error:
        _raise_editor_http_error(error)


@router.post("/projects/{project_id}/editor/redo")
async def redo_editor_revision(
    project_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    service: EditorSessionService = Depends(get_editor_session_service),
):
    _owned_project(db, project_id, user.id)
    try:
        return service.redo(project_id)
    except EditorSessionError as error:
        _raise_editor_http_error(error)
