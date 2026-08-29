import json
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.editor import router
from backend.app.auth.dependencies import require_auth
from backend.app.models.database import Base, Project, User, get_db
from backend.app.services.editor_session_service import EditorSessionService
from backend.tests.test_rect_editor import ROOMS


class EditorSessionApiTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        user = User(
            id=5,
            email="owner@example.com",
            hashed_password="unused",
            full_name="Owner",
        )
        self.project = Project(
            task_id="task-http-editor",
            owner_id=5,
            title="منزل الاختبار",
            status="completed",
            rooms_data=json.dumps(ROOMS),
        )
        self.db.add_all([user, self.project])
        self.db.commit()
        EditorSessionService(self.db).initialize(
            project=self.project,
            scale_confidence=0.96,
            geometry_confidence=0.9,
        )

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_auth] = lambda: user
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()

    def test_http_preview_approve_undo_and_redo_flow(self):
        state = self.client.get(f"/api/projects/{self.project.id}/editor")
        self.assertEqual(state.status_code, 200)
        state_data = state.json()
        wall = state_data["geometry"]["walls"][0]

        preview = self.client.post(
            f"/api/projects/{self.project.id}/editor/previews",
            json={
                "base_revision_id": state_data["revision_id"],
                "wall_id": wall["id"],
                "offset_mm": 500,
                "label_ar": "توسيع غرفة المعيشة",
            },
        )
        self.assertEqual(preview.status_code, 200)
        preview_data = preview.json()
        self.assertEqual(preview_data["status"], "pending")

        approval = self.client.post(
            f"/api/projects/{self.project.id}/editor/previews/{preview_data['preview_id']}/approve",
            json={"structural_review_confirmed": True},
        )
        self.assertEqual(approval.status_code, 200)
        self.assertEqual(approval.json()["revision_number"], 1)

        undone = self.client.post(f"/api/projects/{self.project.id}/editor/undo")
        self.assertEqual(undone.status_code, 200)
        self.assertEqual(undone.json()["revision_number"], 0)

        redone = self.client.post(f"/api/projects/{self.project.id}/editor/redo")
        self.assertEqual(redone.status_code, 200)
        self.assertEqual(redone.json()["revision_number"], 1)

    def test_http_user_can_confirm_the_detected_draft(self):
        response = self.client.post(
            f"/api/projects/{self.project.id}/editor/confirm",
            json={"scale_confirmed": True, "geometry_confirmed": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scale_confidence"], 1.0)
        self.assertEqual(response.json()["geometry_confidence"], 1.0)

    def test_http_discard_removes_the_pending_preview(self):
        state = EditorSessionService(self.db).get_state(self.project.id)
        preview = EditorSessionService(self.db).create_preview(
            project_id=self.project.id,
            base_revision_id=state["revision_id"],
            wall_id=state["geometry"]["walls"][0]["id"],
            offset_mm=200,
            label_ar="تحريك الجدار 20 سم",
        )

        response = self.client.post(
            f"/api/projects/{self.project.id}/editor/previews/{preview['preview_id']}/discard"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["pending_preview"])

    def test_report_uses_the_current_approved_revision(self):
        service = EditorSessionService(self.db)
        state = service.get_state(self.project.id)
        preview = service.create_preview(
            project_id=self.project.id,
            base_revision_id=state["revision_id"],
            wall_id=state["geometry"]["walls"][0]["id"],
            offset_mm=500,
            label_ar="توسيع غرفة المعيشة",
        )
        service.approve_preview(
            project_id=self.project.id,
            preview_id=preview["preview_id"],
            structural_review_confirmed=True,
        )

        response = self.client.get(f"/api/projects/{self.project.id}/report")

        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["project"]["title"], "منزل الاختبار")
        self.assertEqual(report["revision"]["number"], 1)
        self.assertEqual(report["revision"]["label"], "توسيع غرفة المعيشة")
        self.assertAlmostEqual(report["rooms"][0]["area_m2"], 13.5)
        self.assertIn("مراجعة أولية", report["disclaimer_ar"])


if __name__ == "__main__":
    unittest.main()
