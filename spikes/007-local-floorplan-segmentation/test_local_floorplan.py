import unittest

import numpy as np

from local_floorplan import (
    DOOR_ID,
    FLOOR_ID,
    WALL_ID,
    WINDOW_ID,
    extract_room_regions,
    retain_primary_structure,
)


class RoomRegionExtractionTests(unittest.TestCase):
    def test_primary_structure_filter_removes_detached_predictions(self):
        mask = np.zeros((100, 120), dtype=np.uint8)
        mask[25:28, 10:110] = WALL_ID
        mask[87:90, 10:110] = WALL_ID
        mask[25:90, 10:13] = WALL_ID
        mask[25:90, 107:110] = WALL_ID
        mask[25:90, 58:61] = WALL_ID
        mask[50:60, 58:61] = DOOR_ID
        mask[1:15, 2:118] = WINDOW_ID

        cleaned = retain_primary_structure(mask)

        self.assertTrue(np.all(cleaned[1:15, 2:118] == FLOOR_ID))
        self.assertTrue(np.any(cleaned[25:90, 58:61] == WALL_ID))
        self.assertTrue(np.any(cleaned[50:60, 58:61] == DOOR_ID))

    def test_closed_structure_mask_produces_two_interior_rooms(self):
        mask = np.zeros((100, 120), dtype=np.uint8)
        mask[10:13, 10:110] = WALL_ID
        mask[87:90, 10:110] = WALL_ID
        mask[10:90, 10:13] = WALL_ID
        mask[10:90, 107:110] = WALL_ID
        mask[10:90, 58:61] = WALL_ID
        mask[45:55, 58:61] = DOOR_ID

        rooms = extract_room_regions(mask, content_rect=(0, 0, 120, 100))

        self.assertEqual(len(rooms), 2)
        self.assertTrue(all(room["area_px"] > 2500 for room in rooms))

    def test_exterior_component_is_not_reported_as_a_room(self):
        mask = np.zeros((80, 80), dtype=np.uint8)
        mask[20:23, 20:60] = WALL_ID
        mask[57:60, 20:60] = WALL_ID
        mask[20:60, 20:23] = WALL_ID
        mask[20:60, 57:60] = WALL_ID

        rooms = extract_room_regions(mask, content_rect=(0, 0, 80, 80))

        self.assertEqual(len(rooms), 1)
        self.assertGreater(rooms[0]["area_px"], 900)

    def test_tiny_enclosed_artifact_is_not_reported_as_a_room(self):
        mask = np.zeros((200, 200), dtype=np.uint8)
        mask[10:13, 10:190] = WALL_ID
        mask[187:190, 10:190] = WALL_ID
        mask[10:190, 10:13] = WALL_ID
        mask[10:190, 187:190] = WALL_ID
        mask[10:190, 98:101] = WALL_ID
        mask[90:110, 98:101] = DOOR_ID
        mask[40:43, 40:58] = WALL_ID
        mask[55:58, 40:58] = WALL_ID
        mask[40:58, 40:43] = WALL_ID
        mask[40:58, 55:58] = WALL_ID

        rooms = extract_room_regions(mask, content_rect=(0, 0, 200, 200))

        self.assertEqual(len(rooms), 2)


if __name__ == "__main__":
    unittest.main()
