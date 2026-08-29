import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.editor import get_edit_intent_service, router
from backend.app.auth.dependencies import require_auth
from backend.app.models.database import get_db
from backend.app.services.ai_provider import ProviderAuthenticationError


class FakeQuery:
    def filter(self, *_conditions):
        return self

    def first(self):
        return SimpleNamespace(id=7, owner_id=5)


class FakeDatabase:
    def query(self, _model):
        return FakeQuery()


class FakeEditIntentService:
    def __init__(self):
        self.calls = []

    def plan(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "status": "ready",
            "operation": {
                "kind": "move_wall",
                "target_id": "wall-shared",
                "delta_cm": 50.0,
            },
            "explanation": "معاينة مقترحة فقط.",
            "clarification": None,
            "warnings": [],
        }


class EditorApiTests(unittest.TestCase):
    def test_owned_project_can_request_a_typed_edit_intent(self):
        service = FakeEditIntentService()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_auth] = lambda: SimpleNamespace(id=5)
        app.dependency_overrides[get_db] = lambda: FakeDatabase()
        app.dependency_overrides[get_edit_intent_service] = lambda: service
        client = TestClient(app)

        response = client.post(
            "/api/projects/7/edit-intent",
            json={
                "prompt": "حرّك الجدار 50 سم",
                "selection": {
                    "room_id": "room-left",
                    "element_id": "wall-shared",
                    "element_type": "wall",
                },
                "revision": 0,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["operation"]["delta_cm"], 50.0)
        self.assertEqual(service.calls[0]["selection"].element_id, "wall-shared")

    def test_openrouter_authentication_failure_returns_a_safe_service_error(self):
        class AuthenticationFailureService:
            def plan(self, **_kwargs):
                raise ProviderAuthenticationError("secret provider detail")

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_auth] = lambda: SimpleNamespace(id=5)
        app.dependency_overrides[get_db] = lambda: FakeDatabase()
        app.dependency_overrides[get_edit_intent_service] = AuthenticationFailureService
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/api/projects/7/edit-intent",
            json={
                "prompt": "حرّك الجدار 50 سم",
                "selection": {
                    "room_id": "room-left",
                    "element_id": "wall-shared",
                    "element_type": "wall",
                },
                "revision": 0,
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "ai_auth_failed")
        self.assertNotIn("secret provider detail", response.text)

    def test_editor_route_is_registered_in_the_main_application(self):
        from backend.app.main import app

        paths = set(app.openapi()["paths"])

        self.assertIn('/api/projects/{project_id}/edit-intent', paths)


if __name__ == "__main__":
    unittest.main()
