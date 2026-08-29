import os
import tempfile
import unittest

import cv2
import numpy as np
import pymupdf

from backend.app.services.plan_ingestion import prepare_floor_plan


class PlanIngestionTests(unittest.TestCase):
    def test_image_file_is_loaded_without_creating_a_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = os.path.join(directory, "plan.png")
            cv2.imwrite(image_path, np.full((20, 30, 3), 255, dtype=np.uint8))

            with prepare_floor_plan(image_path) as prepared:
                self.assertEqual(prepared.image.shape[:2], (20, 30))
                self.assertEqual(prepared.inference_path, image_path)
                self.assertFalse(prepared.is_temporary)

    def test_pdf_first_page_is_rasterized_and_temporary_copy_is_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = os.path.join(directory, "plan.pdf")
            document = pymupdf.open()
            page = document.new_page(width=240, height=160)
            page.draw_rect(pymupdf.Rect(20, 20, 220, 140), color=(0, 0, 0), width=3)
            document.save(pdf_path)
            document.close()

            with prepare_floor_plan(pdf_path) as prepared:
                raster_path = prepared.inference_path
                self.assertTrue(prepared.is_temporary)
                self.assertTrue(os.path.exists(raster_path))
                self.assertGreater(prepared.image.shape[0], 160)
                self.assertGreater(prepared.image.shape[1], 240)

            self.assertFalse(os.path.exists(raster_path))


if __name__ == "__main__":
    unittest.main()
