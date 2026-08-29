import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import main
from backend.app.api.projects import router as projects_router
from backend.app.auth.dependencies import require_auth
from backend.app.models.database import Base, Project, User, get_db
from backend.app.services.smart_architect import AnalysisPipelineError


class AnalysisTaskPersistenceTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.sessions = sessionmaker(bind=engine)
        db = self.sessions()
        self.user = User(id=1, email="owner@example.com", hashed_password="unused", full_name="Owner")
        db.add(self.user)
        db.add(Project(task_id="analysis-task-1", owner_id=1, title="مخطط اختبار", status="processing"))
        db.commit()
        db.close()

    def tearDown(self):
        main.analysis_results.pop("analysis-task-1", None)

    def test_pipeline_error_is_persisted_as_a_safe_user_facing_failure(self):
        with (
            patch.object(main, "SessionLocal", self.sessions),
            patch.object(
                main.architect,
                "analyze",
                side_effect=AnalysisPipelineError("room_detection_empty"),
            ),
        ):
            main.process_floor_plan(
                "analysis-task-1",
                "unused-plan.png",
                {},
                "http://testserver",
            )

        db = self.sessions()
        project = db.query(Project).filter(Project.task_id == "analysis-task-1").one()
        self.assertEqual(project.status, "failed")
        self.assertEqual(project.analysis_error_code, "room_detection_empty")
        self.assertIn("اكتشاف غرف", project.analysis_error_message)
        self.assertIsNone(project.compliance_score)
        self.assertEqual(main.analysis_results["analysis-task-1"]["error_code"], "room_detection_empty")
        db.close()

    def test_provider_credit_exhaustion_is_persisted_with_an_actionable_safe_message(self):
        with (
            patch.object(main, "SessionLocal", self.sessions),
            patch.object(
                main.architect,
                "analyze",
                side_effect=AnalysisPipelineError("provider_credit_exhausted"),
            ),
        ):
            main.process_floor_plan(
                "analysis-task-1",
                "unused-plan.png",
                {},
                "http://testserver",
            )

        db = self.sessions()
        project = db.query(Project).filter(Project.task_id == "analysis-task-1").one()
        self.assertEqual(project.status, "failed")
        self.assertEqual(project.analysis_error_code, "provider_credit_exhausted")
        self.assertIn("رصيد", project.analysis_error_message)
        self.assertNotIn("Roboflow", project.analysis_error_message)
        db.close()

    def test_missing_local_model_is_persisted_with_setup_guidance(self):
        with (
            patch.object(main, "SessionLocal", self.sessions),
            patch.object(
                main.architect,
                "analyze",
                side_effect=AnalysisPipelineError("local_model_missing"),
            ),
        ):
            main.process_floor_plan(
                "analysis-task-1",
                "unused-plan.png",
                {},
                "http://testserver",
            )

        db = self.sessions()
        project = db.query(Project).filter(Project.task_id == "analysis-task-1").one()
        self.assertEqual(project.status, "failed")
        self.assertEqual(project.analysis_error_code, "local_model_missing")
        self.assertIn("النموذج المحلي", project.analysis_error_message)
        self.assertIn("إعداد", project.analysis_error_message)
        self.assertNotIn("safetensors", project.analysis_error_message)
        db.close()

    def test_project_api_exposes_the_safe_analysis_failure(self):
        db = self.sessions()
        project = db.query(Project).filter(Project.task_id == "analysis-task-1").one()
        project.status = "failed"
        project.analysis_error_code = "compliance_failed"
        project.analysis_error_message = "تعذر إكمال فحص المتطلبات. لم تُحسب درجة امتثال للمخطط."
        db.commit()
        project_id = project.id

        app = FastAPI()
        app.include_router(projects_router)
        app.dependency_overrides[require_auth] = lambda: SimpleNamespace(id=1)
        app.dependency_overrides[get_db] = lambda: db
        response = TestClient(app).get(f"/api/projects/{project_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis_error_code"], "compliance_failed")
        self.assertIn("فحص المتطلبات", response.json()["analysis_error_message"])
        db.close()


if __name__ == "__main__":
    unittest.main()
