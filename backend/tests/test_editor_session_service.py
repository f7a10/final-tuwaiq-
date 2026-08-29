import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models.database import Base, EditorPreview, EditorRevision, EditorSession, Project
from backend.app.services.editor_session_service import EditorSessionError, EditorSessionService
from backend.tests.test_rect_editor import ROOMS


class EditorSessionPersistenceTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.project = Project(
            task_id="task-persist",
            owner_id=None,
            title="منزل الاختبار",
            status="completed",
            rooms_data=json.dumps(ROOMS),
        )
        self.db.add(self.project)
        self.db.commit()
        self.service = EditorSessionService(self.db)

    def tearDown(self):
        self.db.close()

    def test_preview_approval_reload_undo_and_redo_are_persisted(self):
        state = self.service.initialize(
            project=self.project,
            scale_confidence=0.96,
            geometry_confidence=0.9,
        )
        shared_wall = state["geometry"]["walls"][0]

        preview = self.service.create_preview(
            project_id=self.project.id,
            base_revision_id=state["revision_id"],
            wall_id=shared_wall["id"],
            offset_mm=500,
            label_ar="توسيع غرفة المعيشة",
        )

        self.assertEqual(preview["base_revision_id"], state["revision_id"])
        self.assertEqual(self.service.get_state(self.project.id)["revision_number"], 0)
        with self.assertRaisesRegex(EditorSessionError, "structural_review_required"):
            self.service.approve_preview(
                project_id=self.project.id,
                preview_id=preview["preview_id"],
                structural_review_confirmed=False,
            )

        approved = self.service.approve_preview(
            project_id=self.project.id,
            preview_id=preview["preview_id"],
            structural_review_confirmed=True,
        )
        self.assertEqual(approved["revision_number"], 1)

        reloaded = EditorSessionService(self.db).get_state(self.project.id)
        self.assertEqual(reloaded["revision_id"], approved["revision_id"])
        self.assertTrue(reloaded["can_undo"])

        undone = self.service.undo(self.project.id)
        self.assertEqual(undone["revision_number"], 0)
        self.assertTrue(undone["can_redo"])

        redone = self.service.redo(self.project.id)
        self.assertEqual(redone["revision_id"], approved["revision_id"])
        self.assertFalse(redone["can_redo"])

        self.assertEqual(self.db.query(EditorSession).count(), 1)
        self.assertEqual(self.db.query(EditorRevision).count(), 2)
        self.assertEqual(self.db.query(EditorPreview).count(), 1)

    def test_user_confirmation_unlocks_a_preliminary_draft_without_auto_certifying_structure(self):
        state = self.service.initialize(
            project=self.project,
            scale_confidence=0.45,
            geometry_confidence=0.65,
        )
        wall = state["geometry"]["walls"][0]
        preview = self.service.create_preview(
            project_id=self.project.id,
            base_revision_id=state["revision_id"],
            wall_id=wall["id"],
            offset_mm=300,
            label_ar="تحريك الجدار 30 سم",
        )

        with self.assertRaisesRegex(EditorSessionError, "scale_calibration_required"):
            self.service.approve_preview(
                project_id=self.project.id,
                preview_id=preview["preview_id"],
                structural_review_confirmed=True,
            )

        confirmed = self.service.confirm_draft(
            project_id=self.project.id,
            scale_confirmed=True,
            geometry_confirmed=True,
        )

        self.assertEqual(confirmed["scale_confidence"], 1.0)
        self.assertEqual(confirmed["geometry_confidence"], 1.0)
        approved = self.service.approve_preview(
            project_id=self.project.id,
            preview_id=preview["preview_id"],
            structural_review_confirmed=True,
        )
        self.assertEqual(approved["revision_number"], 1)

    def test_discarded_preview_does_not_return_after_reload(self):
        state = self.service.initialize(
            project=self.project,
            scale_confidence=0.96,
            geometry_confidence=0.9,
        )
        preview = self.service.create_preview(
            project_id=self.project.id,
            base_revision_id=state["revision_id"],
            wall_id=state["geometry"]["walls"][0]["id"],
            offset_mm=200,
            label_ar="تحريك الجدار 20 سم",
        )

        reloaded = self.service.discard_preview(
            project_id=self.project.id,
            preview_id=preview["preview_id"],
        )

        self.assertIsNone(reloaded["pending_preview"])
        stored = self.db.get(EditorPreview, preview["preview_id"])
        self.assertEqual(stored.status, "discarded")


if __name__ == "__main__":
    unittest.main()
