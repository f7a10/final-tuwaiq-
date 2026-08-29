from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from itertools import combinations
from math import hypot
from typing import Any

from shapely.geometry import Polygon


@dataclass
class Vertex:
    x: float
    y: float


@dataclass
class Wall:
    id: str
    start_vertex: str
    end_vertex: str
    locked: bool = False
    kind: str = "interior"


@dataclass
class Room:
    id: str
    vertex_ids: list[str]


@dataclass
class Opening:
    id: str
    wall_id: str
    center_ratio: float
    width: float
    kind: str = "door"


@dataclass
class Plan:
    vertices: dict[str, Vertex]
    walls: dict[str, Wall]
    rooms: dict[str, Room]
    openings: dict[str, Opening]
    footprint_vertex_ids: list[str]
    minimum_safe_span: float = 0.8
    minimum_opening_edge_clearance: float = 0.1
    scale_confidence: float = 1.0
    geometry_confidence: float = 1.0
    minimum_edit_confidence: float = 0.8


@dataclass
class TransactionResult:
    accepted: bool
    plan: Plan
    errors: list[str] = field(default_factory=list)


def make_two_room_plan() -> Plan:
    vertices = {
        "v00": Vertex(0.0, 0.0),
        "v10": Vertex(4.0, 0.0),
        "v20": Vertex(8.0, 0.0),
        "v01": Vertex(0.0, 3.0),
        "v11": Vertex(4.0, 3.0),
        "v21": Vertex(8.0, 3.0),
    }
    walls = {
        "top-left": Wall("top-left", "v00", "v10", locked=True, kind="exterior"),
        "top-right": Wall("top-right", "v10", "v20", locked=True, kind="exterior"),
        "bottom-left": Wall("bottom-left", "v01", "v11", locked=True, kind="exterior"),
        "bottom-right": Wall("bottom-right", "v11", "v21", locked=True, kind="exterior"),
        "left": Wall("left", "v00", "v01", locked=True, kind="exterior"),
        "shared": Wall("shared", "v10", "v11"),
        "right": Wall("right", "v20", "v21", locked=True, kind="exterior"),
    }
    rooms = {
        "left": Room("left", ["v00", "v10", "v11", "v01"]),
        "right": Room("right", ["v10", "v20", "v21", "v11"]),
    }
    openings = {
        "shared-door": Opening(
            "shared-door",
            wall_id="shared",
            center_ratio=0.5,
            width=0.9,
        ),
        "entrance-door": Opening(
            "entrance-door",
            wall_id="left",
            center_ratio=0.5,
            width=0.9,
        ),
    }
    return Plan(
        vertices=vertices,
        walls=walls,
        rooms=rooms,
        openings=openings,
        footprint_vertex_ids=["v00", "v20", "v21", "v01"],
    )


def _point(plan: Plan, vertex_id: str) -> tuple[float, float]:
    vertex = plan.vertices[vertex_id]
    return vertex.x, vertex.y


def room_polygon(plan: Plan, room_id: str) -> Polygon:
    room = plan.rooms[room_id]
    return Polygon([_point(plan, vertex_id) for vertex_id in room.vertex_ids])


def room_area(plan: Plan, room_id: str) -> float:
    return room_polygon(plan, room_id).area


def footprint_polygon(plan: Plan) -> Polygon:
    return Polygon(
        [_point(plan, vertex_id) for vertex_id in plan.footprint_vertex_ids]
    )


def opening_segment(
    plan: Plan,
    opening_id: str,
) -> tuple[tuple[float, float], tuple[float, float]]:
    opening = plan.openings[opening_id]
    wall = plan.walls[opening.wall_id]
    start = _point(plan, wall.start_vertex)
    end = _point(plan, wall.end_vertex)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = hypot(dx, dy)
    if length == 0:
        raise ValueError(f"Wall {wall.id} has zero length")

    unit_x = dx / length
    unit_y = dy / length
    center_x = start[0] + dx * opening.center_ratio
    center_y = start[1] + dy * opening.center_ratio
    half_width = opening.width / 2
    return (
        (center_x - unit_x * half_width, center_y - unit_y * half_width),
        (center_x + unit_x * half_width, center_y + unit_y * half_width),
    )


def _move_wall(plan: Plan, wall_id: str, offset: float) -> None:
    wall = plan.walls[wall_id]
    if wall.locked:
        raise ValueError(f"Wall {wall.id} is locked")

    start = plan.vertices[wall.start_vertex]
    end = plan.vertices[wall.end_vertex]

    if abs(start.x - end.x) < 1e-9:
        start.x += offset
        end.x += offset
        return
    if abs(start.y - end.y) < 1e-9:
        start.y += offset
        end.y += offset
        return
    raise ValueError("The first spike supports orthogonal wall movement only")


def _wall_length(plan: Plan, wall_id: str) -> float:
    wall = plan.walls[wall_id]
    start = plan.vertices[wall.start_vertex]
    end = plan.vertices[wall.end_vertex]
    return hypot(end.x - start.x, end.y - start.y)


def _move_opening(plan: Plan, opening_id: str, center_offset: float) -> None:
    opening = plan.openings[opening_id]
    wall_length = _wall_length(plan, opening.wall_id)
    if wall_length == 0:
        raise ValueError(f"Wall {opening.wall_id} has zero length")
    opening.center_ratio = center_offset / wall_length


def _add_opening(
    plan: Plan,
    opening_id: str,
    wall_id: str,
    center_offset: float,
    width: float,
    kind: str,
) -> None:
    if opening_id in plan.openings:
        raise ValueError(f"Opening {opening_id} already exists")
    wall_length = _wall_length(plan, wall_id)
    if wall_length == 0:
        raise ValueError(f"Wall {wall_id} has zero length")
    plan.openings[opening_id] = Opening(
        id=opening_id,
        wall_id=wall_id,
        center_ratio=center_offset / wall_length,
        width=width,
        kind=kind,
    )


def _remove_opening(plan: Plan, opening_id: str) -> None:
    if opening_id not in plan.openings:
        raise ValueError(f"Opening {opening_id} does not exist")
    del plan.openings[opening_id]


def _resize_opening(plan: Plan, opening_id: str, width: float) -> None:
    opening = plan.openings[opening_id]
    opening.width = width


def _validate_room_polygons(plan: Plan) -> list[str]:
    errors: list[str] = []
    for room_id in plan.rooms:
        polygon = room_polygon(plan, room_id)
        if not polygon.is_valid or polygon.area <= 1e-9:
            errors.append(f"Room {room_id} has an invalid polygon boundary")
    return errors


def _validate_room_boundary_walls(plan: Plan) -> list[str]:
    wall_edges = {
        frozenset((wall.start_vertex, wall.end_vertex))
        for wall in plan.walls.values()
    }
    errors: list[str] = []
    for room in plan.rooms.values():
        boundary = room.vertex_ids
        for start_vertex, end_vertex in zip(
            boundary,
            boundary[1:] + boundary[:1],
        ):
            if frozenset((start_vertex, end_vertex)) not in wall_edges:
                errors.append(
                    f"Room {room.id} boundary edge {start_vertex}-{end_vertex} "
                    "has no wall"
                )
    return errors


def _validate_room_overlaps(plan: Plan) -> list[str]:
    errors: list[str] = []
    for first_id, second_id in combinations(plan.rooms, 2):
        first = room_polygon(plan, first_id)
        second = room_polygon(plan, second_id)
        if not first.is_valid or not second.is_valid:
            continue
        if first.intersection(second).area > 1e-9:
            errors.append(f"Rooms {first_id} and {second_id} overlap")
    return errors


def _validate_minimum_room_spans(plan: Plan) -> list[str]:
    errors: list[str] = []
    for room_id in plan.rooms:
        min_x, min_y, max_x, max_y = room_polygon(plan, room_id).bounds
        minimum_span = min(max_x - min_x, max_y - min_y)
        if minimum_span < plan.minimum_safe_span:
            errors.append(
                f"Room {room_id} minimum span {minimum_span:.3f}m is below "
                f"the geometry safety limit {plan.minimum_safe_span:.3f}m"
            )
    return errors


def _validate_rooms_inside_footprint(plan: Plan) -> list[str]:
    footprint = footprint_polygon(plan)
    errors: list[str] = []
    for room_id in plan.rooms:
        if not footprint.covers(room_polygon(plan, room_id)):
            errors.append(f"Room {room_id} is outside the locked building footprint")
    return errors


def _validate_opening_host_walls(plan: Plan) -> list[str]:
    errors: list[str] = []
    for opening in plan.openings.values():
        if opening.wall_id not in plan.walls:
            errors.append(
                f"Opening {opening.id} has missing host wall {opening.wall_id}"
            )
    return errors


def _validate_opening_widths(plan: Plan) -> list[str]:
    return [
        f"Opening {opening.id} must have a positive width"
        for opening in plan.openings.values()
        if opening.width <= 0
    ]


def _validate_opening_edge_clearances(plan: Plan) -> list[str]:
    errors: list[str] = []
    for opening in plan.openings.values():
        if opening.wall_id not in plan.walls:
            continue
        wall_length = _wall_length(plan, opening.wall_id)
        center_offset = opening.center_ratio * wall_length
        start_offset = center_offset - opening.width / 2
        end_offset = center_offset + opening.width / 2
        if (
            start_offset < plan.minimum_opening_edge_clearance
            or wall_length - end_offset < plan.minimum_opening_edge_clearance
        ):
            errors.append(
                f"Opening {opening.id} violates the required wall edge clearance"
            )
    return errors


def _validate_opening_overlaps(plan: Plan) -> list[str]:
    errors: list[str] = []
    for first, second in combinations(plan.openings.values(), 2):
        if first.wall_id != second.wall_id:
            continue
        if first.wall_id not in plan.walls:
            continue
        wall_length = _wall_length(plan, first.wall_id)
        first_center = first.center_ratio * wall_length
        second_center = second.center_ratio * wall_length
        first_interval = (
            first_center - first.width / 2,
            first_center + first.width / 2,
        )
        second_interval = (
            second_center - second.width / 2,
            second_center + second.width / 2,
        )
        overlap = min(first_interval[1], second_interval[1]) - max(
            first_interval[0], second_interval[0]
        )
        if overlap > 1e-9:
            errors.append(f"Openings {first.id} and {second.id} overlap")
    return errors


def _validate_room_reachability(plan: Plan) -> list[str]:
    edge_to_wall = {
        frozenset((wall.start_vertex, wall.end_vertex)): wall.id
        for wall in plan.walls.values()
    }
    wall_to_rooms: dict[str, list[str]] = {wall_id: [] for wall_id in plan.walls}
    for room in plan.rooms.values():
        boundary = room.vertex_ids
        for start_vertex, end_vertex in zip(
            boundary,
            boundary[1:] + boundary[:1],
        ):
            wall_id = edge_to_wall.get(frozenset((start_vertex, end_vertex)))
            if wall_id is not None:
                wall_to_rooms[wall_id].append(room.id)

    outside = "__outside__"
    adjacency: dict[str, set[str]] = {
        node: set() for node in [outside, *plan.rooms]
    }
    for opening in plan.openings.values():
        if opening.kind != "door" or opening.wall_id not in plan.walls:
            continue
        adjacent_rooms = list(dict.fromkeys(wall_to_rooms[opening.wall_id]))
        if len(adjacent_rooms) == 1:
            room_id = adjacent_rooms[0]
            adjacency[outside].add(room_id)
            adjacency[room_id].add(outside)
        elif len(adjacent_rooms) == 2:
            first, second = adjacent_rooms
            adjacency[first].add(second)
            adjacency[second].add(first)

    visited = {outside}
    frontier = [outside]
    while frontier:
        node = frontier.pop()
        for neighbour in adjacency[node] - visited:
            visited.add(neighbour)
            frontier.append(neighbour)

    return [
        f"Room {room_id} is unreachable from an exterior door"
        for room_id in plan.rooms
        if room_id not in visited
    ]


def apply_transaction(plan: Plan, operations: list[dict[str, Any]]) -> TransactionResult:
    readiness_errors: list[str] = []
    if operations:
        if plan.scale_confidence < plan.minimum_edit_confidence:
            readiness_errors.append(
                f"Scale confidence {plan.scale_confidence:.0%} is below the "
                f"editing threshold {plan.minimum_edit_confidence:.0%}"
            )
        if plan.geometry_confidence < plan.minimum_edit_confidence:
            readiness_errors.append(
                f"Geometry confidence {plan.geometry_confidence:.0%} is below the "
                f"editing threshold {plan.minimum_edit_confidence:.0%}"
            )
    if readiness_errors:
        return TransactionResult(False, plan, readiness_errors)

    preview = deepcopy(plan)
    operation_index = 0
    try:
        for operation_index, operation in enumerate(operations, start=1):
            operation_type = operation.get("type")
            if operation_type == "move_wall":
                _move_wall(
                    preview,
                    wall_id=str(operation["wall_id"]),
                    offset=float(operation["offset"]),
                )
            elif operation_type == "move_opening":
                _move_opening(
                    preview,
                    opening_id=str(operation["opening_id"]),
                    center_offset=float(operation["center_offset"]),
                )
            elif operation_type == "add_opening":
                _add_opening(
                    preview,
                    opening_id=str(operation["opening_id"]),
                    wall_id=str(operation["wall_id"]),
                    center_offset=float(operation["center_offset"]),
                    width=float(operation["width"]),
                    kind=str(operation["kind"]),
                )
            elif operation_type == "remove_opening":
                _remove_opening(
                    preview,
                    opening_id=str(operation["opening_id"]),
                )
            elif operation_type == "resize_opening":
                _resize_opening(
                    preview,
                    opening_id=str(operation["opening_id"]),
                    width=float(operation["width"]),
                )
            else:
                raise ValueError("Unsupported operation")
    except (KeyError, TypeError, ValueError) as exc:
        return TransactionResult(
            False,
            plan,
            [f"Operation {operation_index}: {exc}"],
        )

    validation_errors = [
        *_validate_room_polygons(preview),
        *_validate_room_boundary_walls(preview),
        *_validate_room_overlaps(preview),
        *_validate_minimum_room_spans(preview),
        *_validate_rooms_inside_footprint(preview),
        *_validate_opening_host_walls(preview),
        *_validate_opening_widths(preview),
        *_validate_opening_edge_clearances(preview),
        *_validate_opening_overlaps(preview),
        *_validate_room_reachability(preview),
    ]
    if validation_errors:
        return TransactionResult(False, plan, validation_errors)

    return TransactionResult(True, preview)
