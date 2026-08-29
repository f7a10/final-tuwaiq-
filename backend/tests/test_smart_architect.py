import unittest
from contextlib import contextmanager
from unittest.mock import Mock, patch

import numpy as np

from backend.app.services.plan_ingestion import PreparedFloorPlan
from backend.app.services.floorplan_detector import (
    DetectedOpening,
    DetectedRoom,
    FloorPlanDetections,
    FloorPlanDetectorError,
    PixelBox,
)
from backend.app.services.smart_architect import AnalysisPipelineError, SmartArchitect


def _one_room_detections(*, rooms=True):
    detected_rooms = (
        DetectedRoom(
            id="room-1",
            box=PixelBox(30, 30, 40, 40),
            polygon=((30, 30), (70, 30), (70, 70), (30, 70)),
            area_px=1600,
        ),
    ) if rooms else ()
    return FloorPlanDetections(
        provider="local",
        image_width=100,
        image_height=100,
        wall_polygons=(((20, 20), (80, 20), (80, 25), (20, 25)),),
        doors=(),
        windows=(),
        rooms=detected_rooms,
        inference_seconds=0.1,
    )


class SmartArchitectIngestionTests(unittest.TestCase):
    def test_detector_geometry_is_preserved_while_llm_only_labels_the_room(self):
        room_polygon = ((10, 10), (40, 10), (40, 40), (10, 40))
        detections = FloorPlanDetections(
            provider="local",
            image_width=100,
            image_height=100,
            wall_polygons=(((0, 0), (90, 0), (90, 5), (0, 5)),),
            doors=(
                DetectedOpening(
                    id="door-1",
                    kind="door",
                    box=PixelBox(20, 8, 10, 5),
                    polygon=((20, 8), (30, 8), (30, 13), (20, 13)),
                ),
            ),
            windows=(
                DetectedOpening(
                    id="window-1",
                    kind="window",
                    box=PixelBox(32, 8, 10, 5),
                    polygon=((32, 8), (42, 8), (42, 13), (32, 13)),
                ),
            ),
            rooms=(
                DetectedRoom(
                    id="room-1",
                    box=PixelBox(10, 10, 30, 30),
                    polygon=room_polygon,
                    area_px=900,
                ),
            ),
            inference_seconds=0.2,
        )
        detector = Mock()
        detector.detect.return_value = detections
        architect = object.__new__(SmartArchitect)
        architect.detector = detector
        architect.identify_room_type = Mock(return_value="Bedroom")
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        compliance = {
            "summary": {"violations_total": 0, "warnings_total": 0},
            "violations": [],
        }

        with patch(
            "backend.app.services.smart_architect.analyze_plan",
            return_value=compliance,
        ):
            result, _annotated = architect._analyze_image(
                image=image,
                inference_path="plan.jpg",
                task_id="task-1",
            )

        detector.detect.assert_called_once_with(image, inference_path="plan.jpg")
        self.assertEqual(result["rooms"][0]["type"], "Bedroom")
        self.assertEqual(result["rooms"][0]["polygon"], [list(point) for point in room_polygon])
        self.assertEqual(result["geometry"]["provider"], "local")
        self.assertEqual(len(result["geometry"]["walls"]), 1)
        self.assertEqual(len(result["geometry"]["doors"]), 1)
        self.assertEqual(len(result["geometry"]["windows"]), 1)

    def test_local_detector_failure_is_exposed_as_pipeline_error(self):
        detector = Mock()
        detector.detect.side_effect = FloorPlanDetectorError("local_model_missing")
        architect = object.__new__(SmartArchitect)
        architect.detector = detector

        with self.assertRaisesRegex(AnalysisPipelineError, "local_model_missing"):
            architect._analyze_image(
                image=np.zeros((100, 100, 3), dtype=np.uint8),
                inference_path="plan.jpg",
                task_id="task-1",
            )

    def test_room_identification_uses_the_configured_vision_role(self):
        class FakeVisionProvider:
            def __init__(self):
                self.calls = []

            def complete_text(self, **kwargs):
                self.calls.append(kwargs)
                return "Bedroom"

        provider = FakeVisionProvider()
        architect = object.__new__(SmartArchitect)
        architect.ai_provider = provider
        room_crop = np.zeros((20, 20, 3), dtype=np.uint8)

        result = architect.identify_room_type(room_crop)

        self.assertEqual(result, "Bedroom")
        self.assertEqual(provider.calls[0]["role"], "vision")
        content = provider.calls[0]["messages"][0]["content"]
        self.assertEqual(content[1]["type"], "image_url")
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))

    def test_analyze_uses_the_prepared_raster_path(self):
        image = np.zeros((12, 18, 3), dtype=np.uint8)
        lifecycle = []

        @contextmanager
        def fake_prepare(path):
            lifecycle.append(("enter", path))
            try:
                yield PreparedFloorPlan(
                    image=image,
                    inference_path="temporary-raster.jpg",
                    is_temporary=True,
                )
            finally:
                lifecycle.append(("exit", path))

        architect = object.__new__(SmartArchitect)
        architect._analyze_image = Mock(return_value=({"status": "ok"}, image))

        with patch(
            "backend.app.services.smart_architect.prepare_floor_plan",
            fake_prepare,
            create=True,
        ):
            result = architect.analyze("plan.pdf", task_id="task-1")

        self.assertEqual(result[0]["status"], "ok")
        architect._analyze_image.assert_called_once_with(
            image=image,
            inference_path="temporary-raster.jpg",
            task_id="task-1",
        )
        self.assertEqual(lifecycle, [("enter", "plan.pdf"), ("exit", "plan.pdf")])

    def test_room_detection_failure_stops_analysis_instead_of_returning_success(self):
        architect = object.__new__(SmartArchitect)
        architect.detector = Mock()
        architect.detector.detect.side_effect = FloorPlanDetectorError("room_detection_failed")
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        with self.assertRaisesRegex(AnalysisPipelineError, "room_detection_failed"):
            architect._analyze_image(
                image=image,
                inference_path="plan.jpg",
                task_id="task-1",
            )

    def test_credit_exhaustion_is_distinct_and_stops_before_a_second_provider_call(self):
        architect = object.__new__(SmartArchitect)
        architect.detector = Mock()
        architect.detector.detect.side_effect = FloorPlanDetectorError(
            "provider_credit_exhausted"
        )
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        with self.assertRaisesRegex(AnalysisPipelineError, "provider_credit_exhausted"):
            architect._analyze_image(
                image=image,
                inference_path="plan.jpg",
                task_id="task-1",
            )

        architect.detector.detect.assert_called_once_with(
            image,
            inference_path="plan.jpg",
        )

    def test_empty_room_detection_stops_analysis_instead_of_returning_success(self):
        architect = object.__new__(SmartArchitect)
        architect.detector = Mock()
        architect.detector.detect.return_value = _one_room_detections(rooms=False)
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        with self.assertRaisesRegex(AnalysisPipelineError, "room_detection_empty"):
            architect._analyze_image(
                image=image,
                inference_path="plan.jpg",
                task_id="task-1",
            )

    def test_compliance_engine_failure_cannot_become_zero_violations(self):
        architect = object.__new__(SmartArchitect)
        architect.detector = Mock()
        architect.detector.detect.return_value = _one_room_detections()
        architect.identify_room_type = Mock(return_value="Bedroom")
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch(
            "backend.app.services.smart_architect.analyze_plan",
            side_effect=RuntimeError("rules unavailable"),
        ):
            with self.assertRaisesRegex(AnalysisPipelineError, "compliance_failed"):
                architect._analyze_image(
                    image=image,
                    inference_path="plan.jpg",
                    task_id="task-1",
                )


if __name__ == "__main__":
    unittest.main()
