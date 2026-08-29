import os
import unittest
from pathlib import Path

import cv2
import numpy as np

from backend.app.config import LOCAL_FLOORPLAN_MODEL_PATH, PROJECT_ROOT
from backend.app.services.floorplan_detector import (
    FloorPlanDetectorError,
    LocalCubiCasaDetector,
    extract_room_regions,
    filter_openings_near_walls,
    select_primary_wall_component,
)


class LocalFloorPlanPostprocessingTests(unittest.TestCase):
    def test_primary_wall_component_removes_detached_title_banner(self):
        wall_mask = np.zeros((120, 160), dtype=np.uint8)
        wall_mask[35:39, 15:145] = 1
        wall_mask[105:109, 15:145] = 1
        wall_mask[35:109, 15:19] = 1
        wall_mask[35:109, 141:145] = 1
        wall_mask[35:109, 78:82] = 1
        wall_mask[3:18, 10:150] = 1

        cleaned = select_primary_wall_component(wall_mask)

        self.assertEqual(int(cleaned[3:18, 10:150].sum()), 0)
        self.assertGreater(int(cleaned[35:109, 78:82].sum()), 0)

    def test_openings_far_from_the_primary_wall_are_removed(self):
        wall_mask = np.zeros((100, 120), dtype=np.uint8)
        wall_mask[20:23, 10:110] = 1
        opening_mask = np.zeros_like(wall_mask)
        opening_mask[18:25, 50:60] = 1
        opening_mask[60:70, 50:60] = 1

        cleaned = filter_openings_near_walls(opening_mask, wall_mask, padding_px=4)

        self.assertGreater(int(cleaned[18:25, 50:60].sum()), 0)
        self.assertEqual(int(cleaned[60:70, 50:60].sum()), 0)

    def test_room_extraction_returns_only_closed_interior_regions(self):
        wall_mask = np.zeros((100, 120), dtype=np.uint8)
        wall_mask[10:13, 10:110] = 1
        wall_mask[87:90, 10:110] = 1
        wall_mask[10:90, 10:13] = 1
        wall_mask[10:90, 107:110] = 1
        wall_mask[10:90, 58:61] = 1
        door_mask = np.zeros_like(wall_mask)
        door_mask[45:55, 58:61] = 1

        rooms = extract_room_regions(
            wall_mask=wall_mask,
            door_mask=door_mask,
            window_mask=np.zeros_like(wall_mask),
            content_size=(120, 100),
            original_size=(1200, 1000),
        )

        self.assertEqual(len(rooms), 2)
        self.assertTrue(all(room.id.startswith("room-") for room in rooms))
        self.assertTrue(all(not hasattr(room, "room_type") for room in rooms))
        self.assertTrue(all(room.box.width > 400 for room in rooms))

    def test_missing_model_fails_with_stable_error_code(self):
        detector = LocalCubiCasaDetector(model_path="missing-model.safetensors")
        image = np.zeros((100, 120, 3), dtype=np.uint8)

        with self.assertRaises(FloorPlanDetectorError) as caught:
            detector.detect(image)

        self.assertEqual(caught.exception.code, "local_model_missing")


@unittest.skipUnless(
    Path(LOCAL_FLOORPLAN_MODEL_PATH).exists()
    and Path(PROJECT_ROOT, "test_plan_real.png").exists(),
    "local CubiCasa weights are not installed",
)
class LocalFloorPlanLiveModelTests(unittest.TestCase):
    def test_real_sample_extracts_walls_openings_and_rooms_on_cpu(self):
        image = cv2.imread(str(Path(PROJECT_ROOT, "test_plan_real.png")), cv2.IMREAD_COLOR)
        self.assertIsNotNone(image)
        detector = LocalCubiCasaDetector(
            model_path=LOCAL_FLOORPLAN_MODEL_PATH,
            max_dimension=512,
        )

        result = detector.detect(image)

        self.assertGreater(len(result.wall_polygons), 0)
        self.assertGreaterEqual(len(result.doors), 4)
        self.assertGreaterEqual(len(result.windows), 3)
        self.assertEqual(len(result.rooms), 5)
        self.assertEqual(result.provider, "local")
        self.assertTrue(all(not hasattr(room, "room_type") for room in result.rooms))


if __name__ == "__main__":
    unittest.main()
