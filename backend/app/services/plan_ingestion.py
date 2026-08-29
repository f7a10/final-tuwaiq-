from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
import pymupdf


class PlanIngestionError(ValueError):
    """Raised when an uploaded floor plan cannot be prepared safely."""


@dataclass(frozen=True)
class PreparedFloorPlan:
    image: np.ndarray
    inference_path: str
    is_temporary: bool


@contextmanager
def prepare_floor_plan(file_path: str) -> Iterator[PreparedFloorPlan]:
    path = Path(file_path)
    extension = path.suffix.lower()
    if extension not in {".png", ".jpg", ".jpeg", ".pdf"}:
        raise PlanIngestionError("Unsupported floor plan file type")

    if extension != ".pdf":
        image = cv2.imread(str(path))
        if image is None:
            raise PlanIngestionError("Could not decode floor plan image")
        yield PreparedFloorPlan(image=image, inference_path=str(path), is_temporary=False)
        return

    raster_path: str | None = None
    try:
        with pymupdf.open(str(path)) as document:
            if document.page_count < 1:
                raise PlanIngestionError("PDF does not contain any pages")
            page = document.load_page(0)
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            samples = np.frombuffer(pixmap.samples, dtype=np.uint8)
            rgb = samples.reshape(pixmap.height, pixmap.width, pixmap.n)
            if pixmap.n == 4:
                image = cv2.cvtColor(rgb, cv2.COLOR_RGBA2BGR)
            else:
                image = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        descriptor, raster_path = tempfile.mkstemp(prefix="emad-plan-", suffix=".jpg")
        os.close(descriptor)
        if not cv2.imwrite(raster_path, image):
            raise PlanIngestionError("Could not create temporary PDF raster")

        yield PreparedFloorPlan(
            image=image,
            inference_path=raster_path,
            is_temporary=True,
        )
    except PlanIngestionError:
        raise
    except Exception as error:
        raise PlanIngestionError("Could not decode floor plan PDF") from error
    finally:
        if raster_path and os.path.exists(raster_path):
            os.remove(raster_path)
