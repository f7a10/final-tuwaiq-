from __future__ import annotations

import copy
import statistics
from typing import Any


class GeometryError(ValueError):
    """Raised when a deterministic geometry operation is unsafe."""


def _number(value: Any, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise GeometryError(f"Invalid numeric field: {field}") from error
    if number <= 0:
        raise GeometryError(f"Non-positive numeric field: {field}")
    return number


def build_geometry(
    rooms_data: list[dict[str, Any]],
    *,
    scale_confidence: float,
    geometry_confidence: float,
) -> dict[str, Any]:
    if len(rooms_data) < 2:
        raise GeometryError("At least two detected rooms are required")

    width_scales: list[float] = []
    height_scales: list[float] = []
    for room in rooms_data:
        box = room.get("box") or {}
        metrics = room.get("metrics") or {}
        box_width = _number(box.get("w"), field="box.w")
        box_height = _number(box.get("h"), field="box.h")
        width_scales.append(_number(metrics.get("width"), field="metrics.width") * 1000 / box_width)
        height_scales.append(_number(metrics.get("height"), field="metrics.height") * 1000 / box_height)

    canvas_width_mm = statistics.median(width_scales)
    canvas_height_mm = statistics.median(height_scales)
    rooms: list[dict[str, Any]] = []
    for source in sorted(rooms_data, key=lambda room: str(room.get("id"))):
        box = source["box"]
        x_mm = round(float(box["x"]) * canvas_width_mm)
        y_mm = round(float(box["y"]) * canvas_height_mm)
        width_mm = round(float(box["w"]) * canvas_width_mm)
        height_mm = round(float(box["h"]) * canvas_height_mm)
        rooms.append({
            "id": str(source["id"]),
            "label": str(source.get("type") or source["id"]),
            "x_mm": x_mm,
            "y_mm": y_mm,
            "width_mm": width_mm,
            "height_mm": height_mm,
            "area_m2": round(width_mm * height_mm / 1_000_000, 2),
        })

    walls: list[dict[str, Any]] = []
    horizontal_tolerance = max(100, round(canvas_width_mm * 0.02))
    vertical_tolerance = max(100, round(canvas_height_mm * 0.02))
    for index, first in enumerate(rooms):
        for second in rooms[index + 1:]:
            first_right = first["x_mm"] + first["width_mm"]
            second_right = second["x_mm"] + second["width_mm"]
            first_bottom = first["y_mm"] + first["height_mm"]
            second_bottom = second["y_mm"] + second["height_mm"]

            vertical_pairs = (
                (first, second, first_right, second["x_mm"]),
                (second, first, second_right, first["x_mm"]),
            )
            for negative, positive, negative_edge, positive_edge in vertical_pairs:
                overlap_start = max(negative["y_mm"], positive["y_mm"])
                overlap_end = min(
                    negative["y_mm"] + negative["height_mm"],
                    positive["y_mm"] + positive["height_mm"],
                )
                if abs(negative_edge - positive_edge) <= horizontal_tolerance and overlap_end - overlap_start >= 800:
                    wall_id = f"wall:{negative['id']}:{positive['id']}:v"
                    walls.append({
                        "id": wall_id,
                        "orientation": "vertical",
                        "coordinate_mm": round((negative_edge + positive_edge) / 2),
                        "start_mm": overlap_start,
                        "end_mm": overlap_end,
                        "room_ids": [negative["id"], positive["id"]],
                        "structural_status": "unknown",
                    })
                    break
            else:
                horizontal_pairs = (
                    (first, second, first_bottom, second["y_mm"]),
                    (second, first, second_bottom, first["y_mm"]),
                )
                for negative, positive, negative_edge, positive_edge in horizontal_pairs:
                    overlap_start = max(negative["x_mm"], positive["x_mm"])
                    overlap_end = min(
                        negative["x_mm"] + negative["width_mm"],
                        positive["x_mm"] + positive["width_mm"],
                    )
                    if abs(negative_edge - positive_edge) <= vertical_tolerance and overlap_end - overlap_start >= 800:
                        wall_id = f"wall:{negative['id']}:{positive['id']}:h"
                        walls.append({
                            "id": wall_id,
                            "orientation": "horizontal",
                            "coordinate_mm": round((negative_edge + positive_edge) / 2),
                            "start_mm": overlap_start,
                            "end_mm": overlap_end,
                            "room_ids": [negative["id"], positive["id"]],
                            "structural_status": "unknown",
                        })
                        break

    if not walls:
        raise GeometryError("No editable shared room boundary could be derived")

    return {
        "schema_version": "emad.rect-geometry.v1",
        "canvas": {
            "width_mm": round(canvas_width_mm),
            "height_mm": round(canvas_height_mm),
        },
        "scale_confidence": float(scale_confidence),
        "geometry_confidence": float(geometry_confidence),
        "rooms": rooms,
        "walls": sorted(walls, key=lambda wall: wall["id"]),
    }


def preview_move_wall(
    geometry: dict[str, Any],
    *,
    wall_id: str,
    offset_mm: int,
) -> dict[str, Any]:
    if not isinstance(offset_mm, int) or offset_mm == 0 or abs(offset_mm) > 1500:
        raise GeometryError("Wall offset must be a non-zero integer within 1500 mm")

    preview = copy.deepcopy(geometry)
    wall = next((item for item in preview["walls"] if item["id"] == wall_id), None)
    if wall is None:
        raise GeometryError("Unknown wall")
    negative_id, positive_id = wall["room_ids"]
    rooms = {room["id"]: room for room in preview["rooms"]}
    negative = rooms[negative_id]
    positive = rooms[positive_id]

    if wall["orientation"] == "vertical":
        negative["width_mm"] += offset_mm
        positive["x_mm"] += offset_mm
        positive["width_mm"] -= offset_mm
        dimensions = (negative["width_mm"], positive["width_mm"])
    else:
        negative["height_mm"] += offset_mm
        positive["y_mm"] += offset_mm
        positive["height_mm"] -= offset_mm
        dimensions = (negative["height_mm"], positive["height_mm"])

    if min(dimensions) < 800:
        raise GeometryError("Wall move would create a room span below 800 mm")

    wall["coordinate_mm"] += offset_mm
    for room in (negative, positive):
        room["area_m2"] = round(
            room["width_mm"] * room["height_mm"] / 1_000_000,
            2,
        )
    preview["operation"] = {
        "kind": "move_wall",
        "wall_id": wall_id,
        "offset_mm": offset_mm,
    }
    return preview
