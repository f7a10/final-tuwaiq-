import copy
import unittest

from backend.app.services.rect_editor import build_geometry, preview_move_wall


ROOMS = [
    {
        "id": "room_1",
        "type": "Living Room",
        "metrics": {"width": 4.0, "height": 3.0, "area": 12.0},
        "box": {"x": 0.0, "y": 0.0, "w": 0.5, "h": 1.0},
    },
    {
        "id": "room_2",
        "type": "Bedroom",
        "metrics": {"width": 4.0, "height": 3.0, "area": 12.0},
        "box": {"x": 0.5, "y": 0.0, "w": 0.5, "h": 1.0},
    },
]


class RectEditorTests(unittest.TestCase):
    def test_detected_rooms_create_a_deterministic_shared_wall_preview(self):
        geometry = build_geometry(
            ROOMS,
            scale_confidence=0.96,
            geometry_confidence=0.9,
        )
        original = copy.deepcopy(geometry)

        self.assertEqual(len(geometry["walls"]), 1)
        wall = geometry["walls"][0]
        self.assertEqual(wall["room_ids"], ["room_1", "room_2"])
        self.assertEqual(wall["orientation"], "vertical")
        self.assertEqual(wall["structural_status"], "unknown")

        preview = preview_move_wall(
            geometry,
            wall_id=wall["id"],
            offset_mm=500,
        )

        self.assertEqual(geometry, original)
        areas = {room["id"]: room["area_m2"] for room in preview["rooms"]}
        self.assertAlmostEqual(areas["room_1"], 13.5)
        self.assertAlmostEqual(areas["room_2"], 10.5)
        self.assertEqual(preview["operation"]["offset_mm"], 500)


if __name__ == "__main__":
    unittest.main()
