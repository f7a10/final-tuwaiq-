"""Local and provider-neutral floor-plan detection contracts."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from safetensors.torch import load_file

from backend.app.services.cubicasa_model import CubiCasaStructureModel

Point = tuple[int, int]
Polygon = tuple[Point, ...]
OpeningKind = Literal["door", "window"]


class FloorPlanDetectorError(RuntimeError):
    """A stable, user-safe local/provider detection failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PixelBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2


@dataclass(frozen=True)
class DetectedOpening:
    id: str
    kind: OpeningKind
    box: PixelBox
    polygon: Polygon


@dataclass(frozen=True)
class DetectedRoom:
    id: str
    box: PixelBox
    polygon: Polygon
    area_px: int


@dataclass(frozen=True)
class FloorPlanDetections:
    provider: str
    image_width: int
    image_height: int
    wall_polygons: tuple[Polygon, ...]
    doors: tuple[DetectedOpening, ...]
    windows: tuple[DetectedOpening, ...]
    rooms: tuple[DetectedRoom, ...]
    inference_seconds: float

    def structure_predictions(self) -> list[dict]:
        predictions: list[dict] = []
        for opening in (*self.doors, *self.windows):
            predictions.append(
                {
                    "class": opening.kind,
                    "x": opening.box.center_x,
                    "y": opening.box.center_y,
                    "width": opening.box.width,
                    "height": opening.box.height,
                    "polygon": [list(point) for point in opening.polygon],
                }
            )
        return predictions

    def room_predictions(self) -> list[dict]:
        return [
            {
                "id": room.id,
                "x": room.box.center_x,
                "y": room.box.center_y,
                "width": room.box.width,
                "height": room.box.height,
                "polygon": [list(point) for point in room.polygon],
                "area_px": room.area_px,
            }
            for room in self.rooms
        ]


def select_primary_wall_component(wall_mask: np.ndarray) -> np.ndarray:
    binary = (wall_mask > 0).astype(np.uint8)
    if not np.any(binary):
        return binary
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    connected = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(connected, 8)
    if count <= 1:
        return binary

    candidates = []
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])
        candidates.append((area * min(width, height), area, label))
    primary_label = max(candidates)[2]
    return ((labels == primary_label) & (binary > 0)).astype(np.uint8)


def filter_openings_near_walls(
    opening_mask: np.ndarray,
    wall_mask: np.ndarray,
    *,
    padding_px: int = 4,
) -> np.ndarray:
    openings = (opening_mask > 0).astype(np.uint8)
    if not np.any(openings):
        return openings
    kernel_size = padding_px * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    near_wall = cv2.dilate((wall_mask > 0).astype(np.uint8), kernel, iterations=1) > 0
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(openings, 8)
    cleaned = np.zeros_like(openings)
    for label in range(1, count):
        component = labels == label
        if int(stats[label, cv2.CC_STAT_AREA]) >= 4 and np.any(component & near_wall):
            cleaned[component] = 1
    return cleaned


def _scaled_point(point: Point, scale_x: float, scale_y: float) -> Point:
    return int(round(point[0] * scale_x)), int(round(point[1] * scale_y))


def _component_polygon(component: np.ndarray) -> Polygon:
    contours, _hierarchy = cv2.findContours(
        component.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        return ()
    contour = max(contours, key=cv2.contourArea)
    epsilon = max(1.0, 0.004 * cv2.arcLength(contour, True))
    points = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
    return tuple((int(x), int(y)) for x, y in points)


def _scaled_box(
    x: int,
    y: int,
    width: int,
    height: int,
    scale_x: float,
    scale_y: float,
) -> PixelBox:
    return PixelBox(
        x=int(round(x * scale_x)),
        y=int(round(y * scale_y)),
        width=max(1, int(round(width * scale_x))),
        height=max(1, int(round(height * scale_y))),
    )


def extract_room_regions(
    *,
    wall_mask: np.ndarray,
    door_mask: np.ndarray,
    window_mask: np.ndarray,
    content_size: tuple[int, int],
    original_size: tuple[int, int],
    minimum_area_ratio: float = 0.01,
) -> tuple[DetectedRoom, ...]:
    content_width, content_height = content_size
    original_width, original_height = original_size
    barrier = ((wall_mask > 0) | (door_mask > 0) | (window_mask > 0)).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    barrier = cv2.morphologyEx(barrier, cv2.MORPH_CLOSE, kernel)
    barrier = cv2.dilate(barrier, kernel, iterations=1)

    traversable = (1 - barrier).astype(np.uint8)
    content = np.zeros_like(traversable)
    content[:content_height, :content_width] = 1
    traversable *= content

    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(traversable, 8)
    minimum_area = max(64, int(content_width * content_height * minimum_area_ratio))
    scale_x = original_width / content_width
    scale_y = original_height / content_height
    rooms: list[DetectedRoom] = []

    for label in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[label])
        touches_content_edge = (
            x <= 0
            or y <= 0
            or x + width >= content_width
            or y + height >= content_height
        )
        if touches_content_edge or area < minimum_area:
            continue
        polygon = _component_polygon(labels == label)
        if len(polygon) < 3:
            continue
        rooms.append(
            DetectedRoom(
                id="",
                box=_scaled_box(x, y, width, height, scale_x, scale_y),
                polygon=tuple(_scaled_point(point, scale_x, scale_y) for point in polygon),
                area_px=int(round(area * scale_x * scale_y)),
            )
        )

    rooms.sort(key=lambda room: (room.box.y, room.box.x))
    return tuple(
        DetectedRoom(
            id=f"room-{index}",
            box=room.box,
            polygon=room.polygon,
            area_px=room.area_px,
        )
        for index, room in enumerate(rooms, start=1)
    )


def _extract_openings(
    mask: np.ndarray,
    *,
    kind: OpeningKind,
    content_size: tuple[int, int],
    original_size: tuple[int, int],
) -> tuple[DetectedOpening, ...]:
    content_width, content_height = content_size
    original_width, original_height = original_size
    scale_x = original_width / content_width
    scale_y = original_height / content_height
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        (mask > 0).astype(np.uint8),
        8,
    )
    openings: list[DetectedOpening] = []
    for label in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[label])
        if area < 4 or x >= content_width or y >= content_height:
            continue
        polygon = _component_polygon(labels == label)
        if len(polygon) < 3:
            continue
        openings.append(
            DetectedOpening(
                id="",
                kind=kind,
                box=_scaled_box(x, y, width, height, scale_x, scale_y),
                polygon=tuple(_scaled_point(point, scale_x, scale_y) for point in polygon),
            )
        )
    openings.sort(key=lambda opening: (opening.box.y, opening.box.x))
    return tuple(
        DetectedOpening(
            id=f"{kind}-{index}",
            kind=kind,
            box=opening.box,
            polygon=opening.polygon,
        )
        for index, opening in enumerate(openings, start=1)
    )


def _extract_wall_polygons(
    wall_mask: np.ndarray,
    *,
    content_size: tuple[int, int],
    original_size: tuple[int, int],
) -> tuple[Polygon, ...]:
    content_width, content_height = content_size
    original_width, original_height = original_size
    scale_x = original_width / content_width
    scale_y = original_height / content_height
    contours, _hierarchy = cv2.findContours(
        (wall_mask > 0).astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    polygons: list[Polygon] = []
    for contour in contours:
        if cv2.contourArea(contour) < 20:
            continue
        epsilon = max(1.0, 0.002 * cv2.arcLength(contour, True))
        points = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
        polygon = tuple(
            _scaled_point((int(x), int(y)), scale_x, scale_y)
            for x, y in points
            if x < content_width and y < content_height
        )
        if len(polygon) >= 3:
            polygons.append(polygon)
    return tuple(polygons)


class LocalCubiCasaDetector:
    """CPU-first local detector. Room semantics are intentionally not emitted."""

    def __init__(
        self,
        *,
        model_path: str,
        max_dimension: int = 512,
        device: str = "cpu",
    ) -> None:
        self.model_path = Path(model_path)
        self.max_dimension = max_dimension
        self.device = torch.device(device)
        self._model: CubiCasaStructureModel | None = None

    def _load_model(self) -> CubiCasaStructureModel:
        if self._model is not None:
            return self._model
        if not self.model_path.is_file():
            raise FloorPlanDetectorError("local_model_missing")
        try:
            model = CubiCasaStructureModel(n_classes=44).to(self.device)
            state = load_file(
                str(self.model_path),
                device="cuda" if self.device.type == "cuda" else "cpu",
            )
            model.load_state_dict(state, strict=True)
            model.eval()
        except Exception as error:
            raise FloorPlanDetectorError("local_model_load_failed") from error
        self._model = model
        return model

    def _prepare_image(
        self,
        image: np.ndarray,
    ) -> tuple[torch.Tensor, tuple[int, int]]:
        if image.ndim != 3 or image.shape[2] != 3 or image.size == 0:
            raise FloorPlanDetectorError("local_detection_failed")
        original_height, original_width = image.shape[:2]
        scale = self.max_dimension / max(original_width, original_height)
        content_width = max(32, int(round(original_width * scale)))
        content_height = max(32, int(round(original_height * scale)))
        canvas_width = ((content_width + 31) // 32) * 32
        canvas_height = ((content_height + 31) // 32) * 32

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (content_width, content_height), interpolation=cv2.INTER_AREA)
        canvas = np.full((canvas_height, canvas_width, 3), 255, dtype=np.uint8)
        canvas[:content_height, :content_width] = resized
        tensor = torch.from_numpy(canvas.copy()).permute(2, 0, 1).float()
        tensor = 2 * (tensor / 255.0) - 1
        return tensor.unsqueeze(0), (content_width, content_height)

    def detect(
        self,
        image: np.ndarray,
        *,
        inference_path: str | None = None,
    ) -> FloorPlanDetections:
        model = self._load_model()
        original_height, original_width = image.shape[:2]
        tensor, content_size = self._prepare_image(image)
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                prediction = model(tensor.to(self.device))
                prediction = F.interpolate(
                    prediction,
                    size=tensor.shape[-2:],
                    mode="bilinear",
                    align_corners=False,
                )
        except Exception as error:
            raise FloorPlanDetectorError("local_detection_failed") from error
        inference_seconds = time.perf_counter() - started

        room_classes = prediction[:, 21:33].softmax(dim=1).argmax(dim=1)[0].cpu().numpy()
        icon_classes = prediction[:, 33:44].softmax(dim=1).argmax(dim=1)[0].cpu().numpy()
        content_width, content_height = content_size
        content = np.zeros_like(room_classes, dtype=np.uint8)
        content[:content_height, :content_width] = 1

        wall_mask = select_primary_wall_component((room_classes == 2).astype(np.uint8) * content)
        if not np.any(wall_mask):
            raise FloorPlanDetectorError("wall_detection_empty")
        door_mask = filter_openings_near_walls(
            (icon_classes == 2).astype(np.uint8) * content,
            wall_mask,
        )
        window_mask = filter_openings_near_walls(
            (icon_classes == 1).astype(np.uint8) * content,
            wall_mask,
        )
        original_size = (original_width, original_height)
        rooms = extract_room_regions(
            wall_mask=wall_mask,
            door_mask=door_mask,
            window_mask=window_mask,
            content_size=content_size,
            original_size=original_size,
        )
        if not rooms:
            raise FloorPlanDetectorError("room_detection_empty")

        return FloorPlanDetections(
            provider="local",
            image_width=original_width,
            image_height=original_height,
            wall_polygons=_extract_wall_polygons(
                wall_mask,
                content_size=content_size,
                original_size=original_size,
            ),
            doors=_extract_openings(
                door_mask,
                kind="door",
                content_size=content_size,
                original_size=original_size,
            ),
            windows=_extract_openings(
                window_mask,
                kind="window",
                content_size=content_size,
                original_size=original_size,
            ),
            rooms=rooms,
            inference_seconds=round(inference_seconds, 4),
        )


def _roboflow_error_code(error: Exception, *, fallback: str) -> str:
    status_code = getattr(error, "status_code", None)
    error_text = str(error).lower()
    if status_code == 402 or "credit_cap_exceeded" in error_text:
        return "provider_credit_exhausted"
    return fallback


def _prediction_box(prediction: dict) -> PixelBox:
    width = max(1, int(round(float(prediction.get("width", 1)))))
    height = max(1, int(round(float(prediction.get("height", 1)))))
    center_x = float(prediction.get("x", width / 2))
    center_y = float(prediction.get("y", height / 2))
    return PixelBox(
        x=int(round(center_x - width / 2)),
        y=int(round(center_y - height / 2)),
        width=width,
        height=height,
    )


def _box_polygon(box: PixelBox) -> Polygon:
    return (
        (box.x, box.y),
        (box.x + box.width, box.y),
        (box.x + box.width, box.y + box.height),
        (box.x, box.y + box.height),
    )


class RoboflowFloorPlanDetector:
    """Compatibility adapter for the two existing hosted Roboflow models."""

    def __init__(self, *, client: object) -> None:
        self.client = client

    def detect(
        self,
        image: np.ndarray,
        *,
        inference_path: str | None = None,
    ) -> FloorPlanDetections:
        if not inference_path:
            raise FloorPlanDetectorError("roboflow_inference_path_missing")
        started = time.perf_counter()
        try:
            structure_result = self.client.infer(
                inference_path,
                model_id="cubicasa5k-2-qpmsa/6",
            )
        except Exception as error:
            raise FloorPlanDetectorError(
                _roboflow_error_code(error, fallback="structure_detection_failed")
            ) from error
        try:
            room_result = self.client.infer(
                inference_path,
                model_id="room-detection-6nzte/1",
            )
        except Exception as error:
            raise FloorPlanDetectorError(
                _roboflow_error_code(error, fallback="room_detection_failed")
            ) from error

        structure_predictions = structure_result.get("predictions", [])
        room_predictions = room_result.get("predictions", [])
        if not room_predictions:
            raise FloorPlanDetectorError("room_detection_empty")

        doors: list[DetectedOpening] = []
        windows: list[DetectedOpening] = []
        wall_polygons: list[Polygon] = []
        for prediction in structure_predictions:
            class_name = str(prediction.get("class", "")).lower()
            box = _prediction_box(prediction)
            polygon = _box_polygon(box)
            if "door" in class_name:
                doors.append(
                    DetectedOpening(
                        id=f"door-{len(doors) + 1}",
                        kind="door",
                        box=box,
                        polygon=polygon,
                    )
                )
            elif "window" in class_name:
                windows.append(
                    DetectedOpening(
                        id=f"window-{len(windows) + 1}",
                        kind="window",
                        box=box,
                        polygon=polygon,
                    )
                )
            elif "wall" in class_name:
                wall_polygons.append(polygon)

        rooms: list[DetectedRoom] = []
        for index, prediction in enumerate(room_predictions, start=1):
            box = _prediction_box(prediction)
            rooms.append(
                DetectedRoom(
                    id=f"room-{index}",
                    box=box,
                    polygon=_box_polygon(box),
                    area_px=box.width * box.height,
                )
            )

        image_height, image_width = image.shape[:2]
        return FloorPlanDetections(
            provider="roboflow",
            image_width=image_width,
            image_height=image_height,
            wall_polygons=tuple(wall_polygons),
            doors=tuple(doors),
            windows=tuple(windows),
            rooms=tuple(rooms),
            inference_seconds=round(time.perf_counter() - started, 4),
        )


def build_floorplan_detector(
    *,
    provider: str,
    local_model_path: str,
    local_max_dimension: int,
    roboflow_api_key: str,
    roboflow_client_factory: Callable[..., object] | None = None,
) -> LocalCubiCasaDetector | RoboflowFloorPlanDetector:
    normalized_provider = provider.strip().lower()
    if normalized_provider == "local":
        return LocalCubiCasaDetector(
            model_path=local_model_path,
            max_dimension=local_max_dimension,
        )
    if normalized_provider == "roboflow":
        if not roboflow_api_key:
            raise FloorPlanDetectorError("roboflow_api_key_missing")
        if roboflow_client_factory is None:
            from inference_sdk import InferenceHTTPClient

            roboflow_client_factory = InferenceHTTPClient
        client = roboflow_client_factory(
            api_url="https://detect.roboflow.com",
            api_key=roboflow_api_key,
        )
        return RoboflowFloorPlanDetector(client=client)
    raise FloorPlanDetectorError("detector_provider_invalid")
