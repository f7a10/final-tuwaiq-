import unittest

import numpy as np

from backend.app.services.floorplan_detector import (
    FloorPlanDetectorError,
    LocalCubiCasaDetector,
    RoboflowFloorPlanDetector,
    build_floorplan_detector,
)


class DetectorProviderSelectionTests(unittest.TestCase):
    def test_local_provider_does_not_construct_roboflow_client(self):
        calls = []

        detector = build_floorplan_detector(
            provider="local",
            local_model_path="model.safetensors",
            local_max_dimension=512,
            roboflow_api_key="unused",
            roboflow_client_factory=lambda **kwargs: calls.append(kwargs),
        )

        self.assertIsInstance(detector, LocalCubiCasaDetector)
        self.assertEqual(calls, [])

    def test_roboflow_provider_constructs_legacy_client(self):
        client = object()
        calls = []

        detector = build_floorplan_detector(
            provider="roboflow",
            local_model_path="unused.safetensors",
            local_max_dimension=512,
            roboflow_api_key="configured-key",
            roboflow_client_factory=lambda **kwargs: calls.append(kwargs) or client,
        )

        self.assertIsInstance(detector, RoboflowFloorPlanDetector)
        self.assertIs(detector.client, client)
        self.assertEqual(calls[0]["api_url"], "https://detect.roboflow.com")
        self.assertEqual(calls[0]["api_key"], "configured-key")

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(FloorPlanDetectorError) as caught:
            build_floorplan_detector(
                provider="automatic",
                local_model_path="model.safetensors",
                local_max_dimension=512,
                roboflow_api_key="configured-key",
            )

        self.assertEqual(caught.exception.code, "detector_provider_invalid")


class RoboflowCompatibilityTests(unittest.TestCase):
    def test_legacy_provider_uses_both_existing_model_ids(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            def infer(self, path, *, model_id):
                self.calls.append((path, model_id))
                if model_id.startswith("cubicasa"):
                    return {
                        "predictions": [
                            {"class": "door", "x": 30, "y": 40, "width": 10, "height": 20},
                            {"class": "window", "x": 70, "y": 20, "width": 30, "height": 8},
                        ]
                    }
                return {
                    "predictions": [
                        {"x": 50, "y": 50, "width": 80, "height": 60},
                    ]
                }

        client = FakeClient()
        detector = RoboflowFloorPlanDetector(client=client)

        result = detector.detect(
            np.zeros((100, 100, 3), dtype=np.uint8),
            inference_path="plan.jpg",
        )

        self.assertEqual(
            client.calls,
            [
                ("plan.jpg", "cubicasa5k-2-qpmsa/6"),
                ("plan.jpg", "room-detection-6nzte/1"),
            ],
        )
        self.assertEqual(len(result.doors), 1)
        self.assertEqual(len(result.windows), 1)
        self.assertEqual(len(result.rooms), 1)
        self.assertEqual(result.provider, "roboflow")

    def test_credit_exhaustion_stops_before_room_request(self):
        class ExhaustedClient:
            def __init__(self):
                self.calls = []

            def infer(self, path, *, model_id):
                self.calls.append((path, model_id))
                error = RuntimeError("credit_cap_exceeded")
                error.status_code = 402
                raise error

        client = ExhaustedClient()
        detector = RoboflowFloorPlanDetector(client=client)

        with self.assertRaises(FloorPlanDetectorError) as caught:
            detector.detect(
                np.zeros((100, 100, 3), dtype=np.uint8),
                inference_path="plan.jpg",
            )

        self.assertEqual(caught.exception.code, "provider_credit_exhausted")
        self.assertEqual(client.calls, [("plan.jpg", "cubicasa5k-2-qpmsa/6")])


if __name__ == "__main__":
    unittest.main()
