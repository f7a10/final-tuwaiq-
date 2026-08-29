import json
import unittest

from backend.app.services.edit_intent_service import EditIntentService, EditSelection


class FakeProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete_text(self, **kwargs):
        self.calls.append(kwargs)
        return json.dumps(self.payload, ensure_ascii=False)


class EditIntentServiceTests(unittest.TestCase):
    def test_valid_wall_request_returns_a_typed_preview_operation(self):
        provider = FakeProvider({
            "status": "ready",
            "operation": {
                "kind": "move_wall",
                "target_id": "wall-shared",
                "delta_cm": 50,
            },
            "explanation": "تحريك الجدار المحدد نحو غرفة النوم.",
            "clarification": None,
            "warnings": [],
        })
        service = EditIntentService(provider)

        result = service.plan(
            prompt="حرّك الجدار 50 سم نحو غرفة النوم",
            selection=EditSelection(
                room_id="room-left",
                element_id="wall-shared",
                element_type="wall",
            ),
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["operation"], {
            "kind": "move_wall",
            "target_id": "wall-shared",
            "delta_cm": 50.0,
        })
        self.assertEqual(provider.calls[0]["role"], "planning")
        self.assertEqual(provider.calls[0]["response_format"]["type"], "json_schema")

    def test_ai_cannot_redirect_an_operation_to_an_unselected_element(self):
        provider = FakeProvider({
            "status": "ready",
            "operation": {
                "kind": "move_wall",
                "target_id": "wall-other",
                "delta_cm": 50,
            },
            "explanation": "",
            "clarification": None,
            "warnings": [],
        })
        service = EditIntentService(provider)

        with self.assertRaisesRegex(Exception, "selected element"):
            service.plan(
                prompt="حرّك الجدار",
                selection=EditSelection(
                    room_id="room-left",
                    element_id="wall-shared",
                    element_type="wall",
                ),
            )


if __name__ == "__main__":
    unittest.main()
