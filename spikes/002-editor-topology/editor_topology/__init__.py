from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from math import hypot
from typing import Any, Iterable

from shapely.geometry import GeometryCollection, LineString, MultiPoint, Point, Polygon
from shapely.ops import polygonize, split, unary_union


TOLERANCE = 1e-8


@dataclass
class WallSegment:
    id: str
    lineage_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    lineage_start: float
    lineage_end: float
    locked: bool = False


@dataclass
class RoomFace:
    id: str
    polygon: Polygon


@dataclass
class Opening:
    id: str
    host_lineage_id: str
    center_offset: float
    width: float
    host_wall_id: str
    kind: str = "door"


@dataclass
class TopologyPlan:
    footprint: Polygon
    walls: dict[str, WallSegment]
    rooms: dict[str, RoomFace]
    openings: dict[str, Opening]
    minimum_safe_span: float = 0.8


@dataclass
class TopologyResult:
    accepted: bool
    plan: TopologyPlan
    errors: list[str] = field(default_factory=list)


def _wall_length(wall: WallSegment) -> float:
    return hypot(wall.end[0] - wall.start[0], wall.end[1] - wall.start[1])


def _line(wall: WallSegment) -> LineString:
    return LineString([wall.start, wall.end])


def make_single_room_plan() -> TopologyPlan:
    footprint = Polygon([(0.0, 0.0), (8.0, 0.0), (8.0, 6.0), (0.0, 6.0)])
    walls = {
        "bottom-boundary": WallSegment(
            "bottom-boundary", "bottom-boundary", (0.0, 0.0), (8.0, 0.0), 0.0, 8.0, True
        ),
        "right-boundary": WallSegment(
            "right-boundary", "right-boundary", (8.0, 0.0), (8.0, 6.0), 0.0, 6.0, True
        ),
        "top-boundary": WallSegment(
            "top-boundary", "top-boundary", (0.0, 6.0), (8.0, 6.0), 0.0, 8.0, True
        ),
        "left-boundary": WallSegment(
            "left-boundary", "left-boundary", (0.0, 0.0), (0.0, 6.0), 0.0, 6.0, True
        ),
    }
    rooms = {"main": RoomFace("main", footprint)}
    openings = {
        "entrance": Opening(
            "entrance",
            host_lineage_id="left-boundary",
            center_offset=1.5,
            width=0.9,
            host_wall_id="left-boundary",
        )
    }
    return TopologyPlan(footprint, walls, rooms, openings)


def room_area(plan: TopologyPlan, room_id: str) -> float:
    return plan.rooms[room_id].polygon.area


def wall_ids_for_lineage(plan: TopologyPlan, lineage_id: str) -> list[str]:
    return [
        wall.id
        for wall in sorted(
            plan.walls.values(),
            key=lambda item: (item.lineage_id, item.lineage_start),
        )
        if wall.lineage_id == lineage_id
    ]


def opening_segment(
    plan: TopologyPlan,
    opening_id: str,
) -> tuple[tuple[float, float], tuple[float, float]]:
    opening = plan.openings[opening_id]
    wall = plan.walls[opening.host_wall_id]
    length = _wall_length(wall)
    local_center = opening.center_offset - wall.lineage_start
    unit_x = (wall.end[0] - wall.start[0]) / length
    unit_y = (wall.end[1] - wall.start[1]) / length
    center = (
        wall.start[0] + unit_x * local_center,
        wall.start[1] + unit_y * local_center,
    )
    half_width = opening.width / 2
    return (
        (center[0] - unit_x * half_width, center[1] - unit_y * half_width),
        (center[0] + unit_x * half_width, center[1] + unit_y * half_width),
    )


def _intersection_points(geometry: Any) -> Iterable[Point]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, Point):
        return [geometry]
    if isinstance(geometry, MultiPoint):
        return list(geometry.geoms)
    if isinstance(geometry, GeometryCollection):
        points: list[Point] = []
        for child in geometry.geoms:
            points.extend(_intersection_points(child))
        return points
    return []


def _node_walls(walls: dict[str, WallSegment]) -> dict[str, WallSegment]:
    source_walls = list(walls.values())
    noded: dict[str, WallSegment] = {}
    for wall in source_walls:
        line = _line(wall)
        split_distances = {0.0, line.length}
        for other in source_walls:
            if other.id == wall.id:
                continue
            for point in _intersection_points(line.intersection(_line(other))):
                distance = line.project(point)
                if TOLERANCE < distance < line.length - TOLERANCE:
                    split_distances.add(distance)

        distances = sorted(split_distances)
        is_split = len(distances) > 2
        for index, (start_distance, end_distance) in enumerate(
            zip(distances, distances[1:]),
            start=1,
        ):
            if end_distance - start_distance <= TOLERANCE:
                continue
            start_point = line.interpolate(start_distance)
            end_point = line.interpolate(end_distance)
            child_id = wall.id if not is_split else f"{wall.id}::{index}"
            noded[child_id] = WallSegment(
                id=child_id,
                lineage_id=wall.lineage_id,
                start=(start_point.x, start_point.y),
                end=(end_point.x, end_point.y),
                lineage_start=wall.lineage_start + start_distance,
                lineage_end=wall.lineage_start + end_distance,
                locked=wall.locked,
            )
    return noded


def _compact_wall_lineages(
    walls: dict[str, WallSegment],
) -> dict[str, WallSegment]:
    grouped: dict[str, list[WallSegment]] = {}
    for wall in walls.values():
        grouped.setdefault(wall.lineage_id, []).append(wall)

    compacted: dict[str, WallSegment] = {}
    for lineage_id, lineage_walls in grouped.items():
        ordered = sorted(lineage_walls, key=lambda wall: wall.lineage_start)
        runs: list[list[WallSegment]] = []
        for wall in ordered:
            if not runs:
                runs.append([wall])
                continue
            previous = runs[-1][-1]
            contiguous_offset = abs(previous.lineage_end - wall.lineage_start) <= TOLERANCE
            contiguous_point = Point(previous.end).distance(Point(wall.start)) <= TOLERANCE
            if contiguous_offset and contiguous_point and previous.locked == wall.locked:
                runs[-1].append(wall)
            else:
                runs.append([wall])

        for index, run in enumerate(runs, start=1):
            wall_id = lineage_id if len(runs) == 1 else f"{lineage_id}::{index}"
            compacted[wall_id] = WallSegment(
                id=wall_id,
                lineage_id=lineage_id,
                start=run[0].start,
                end=run[-1].end,
                lineage_start=run[0].lineage_start,
                lineage_end=run[-1].lineage_end,
                locked=run[0].locked,
            )
    return compacted


def _polygonized_faces(plan: TopologyPlan) -> list[Polygon]:
    merged = unary_union([_line(wall) for wall in plan.walls.values()])
    return [
        polygon
        for polygon in polygonize(merged)
        if plan.footprint.covers(polygon)
        and polygon.area > TOLERANCE
    ]


def _remap_openings(plan: TopologyPlan) -> None:
    for opening in plan.openings.values():
        opening_start = opening.center_offset - opening.width / 2
        opening_end = opening.center_offset + opening.width / 2
        candidates = [
            wall
            for wall in plan.walls.values()
            if wall.lineage_id == opening.host_lineage_id
            and wall.lineage_start - TOLERANCE <= opening_start
            and wall.lineage_end + TOLERANCE >= opening_end
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"Opening {opening.id} cannot map to exactly one wall segment"
            )
        opening.host_wall_id = candidates[0].id


def _split_room(plan: TopologyPlan, operation: dict[str, Any]) -> None:
    room_id = str(operation["room_id"])
    target = plan.rooms[room_id].polygon
    start = tuple(float(value) for value in operation["start"])
    end = tuple(float(value) for value in operation["end"])
    cut = LineString([start, end])
    if cut.length <= TOLERANCE:
        raise ValueError("Split wall must have positive length")
    if target.boundary.distance(Point(start)) > TOLERANCE or target.boundary.distance(
        Point(end)
    ) > TOLERANCE:
        raise ValueError("Split wall endpoints must lie on the room boundary")

    split_parts = list(split(target, cut).geoms)
    if len(split_parts) != 2:
        raise ValueError("Split wall must divide the target room into exactly two faces")

    wall_id = str(operation["wall_id"])
    if wall_id in plan.walls:
        raise ValueError(f"Wall {wall_id} already exists")
    plan.walls[wall_id] = WallSegment(
        id=wall_id,
        lineage_id=wall_id,
        start=start,
        end=end,
        lineage_start=0.0,
        lineage_end=cut.length,
    )
    plan.walls = _node_walls(plan.walls)

    derived = _polygonized_faces(plan)
    target_faces = [
        polygon
        for polygon in derived
        if target.covers(polygon.representative_point())
    ]
    if len(target_faces) != 2:
        raise ValueError("Noded wall network did not derive exactly two child rooms")
    if abs(sum(face.area for face in target_faces) - target.area) > TOLERANCE:
        raise ValueError("Derived child rooms do not preserve the target room area")

    child_room_ids = [str(value) for value in operation["child_room_ids"]]
    if len(child_room_ids) != 2 or len(set(child_room_ids)) != 2:
        raise ValueError("Split operation requires two unique child room IDs")
    ordered_faces = sorted(target_faces, key=lambda polygon: (polygon.centroid.y, polygon.centroid.x))
    plan.rooms = {
        child_id: RoomFace(child_id, polygon)
        for child_id, polygon in zip(child_room_ids, ordered_faces)
    }
    _remap_openings(plan)


def _merge_rooms(plan: TopologyPlan, operation: dict[str, Any]) -> None:
    room_ids = [str(value) for value in operation["room_ids"]]
    if len(room_ids) != 2 or len(set(room_ids)) != 2:
        raise ValueError("Merge operation requires two unique room IDs")
    first = plan.rooms[room_ids[0]].polygon
    second = plan.rooms[room_ids[1]].polygon
    shared_boundary = first.boundary.intersection(second.boundary)
    if shared_boundary.length <= TOLERANCE:
        raise ValueError("Rooms must share a wall before they can be merged")

    wall_lineage_id = str(operation["wall_lineage_id"])
    removed_walls = [
        wall
        for wall in plan.walls.values()
        if wall.lineage_id == wall_lineage_id
    ]
    if not removed_walls:
        raise ValueError(f"Wall lineage {wall_lineage_id} does not exist")
    for wall in removed_walls:
        if _line(wall).difference(shared_boundary.buffer(TOLERANCE)).length > TOLERANCE:
            raise ValueError("Selected wall is not the shared room boundary")

    merged_polygon = unary_union([first, second])
    if not isinstance(merged_polygon, Polygon):
        raise ValueError("Merged rooms do not produce one valid polygon")

    plan.walls = {
        wall_id: wall
        for wall_id, wall in plan.walls.items()
        if wall.lineage_id != wall_lineage_id
    }
    plan.walls = _node_walls(_compact_wall_lineages(plan.walls))
    derived = _polygonized_faces(plan)
    matching_faces = [
        polygon
        for polygon in derived
        if polygon.symmetric_difference(merged_polygon).area <= TOLERANCE
    ]
    if len(matching_faces) != 1:
        raise ValueError("Wall removal did not derive exactly one merged room")

    merged_room_id = str(operation["merged_room_id"])
    plan.rooms = {
        merged_room_id: RoomFace(merged_room_id, matching_faces[0])
    }
    _remap_openings(plan)


def _assign_room_ids_by_overlap(
    old_rooms: dict[str, RoomFace],
    derived_faces: list[Polygon],
) -> dict[str, RoomFace]:
    if len(old_rooms) != len(derived_faces):
        raise ValueError("Wall move changed the number of room faces")
    candidates = sorted(
        (
            old_room.polygon.intersection(face).area,
            room_id,
            face_index,
        )
        for room_id, old_room in old_rooms.items()
        for face_index, face in enumerate(derived_faces)
    )
    assigned_rooms: set[str] = set()
    assigned_faces: set[int] = set()
    assignments: dict[str, RoomFace] = {}
    for overlap_area, room_id, face_index in reversed(candidates):
        if overlap_area <= TOLERANCE:
            continue
        if room_id in assigned_rooms or face_index in assigned_faces:
            continue
        assignments[room_id] = RoomFace(room_id, derived_faces[face_index])
        assigned_rooms.add(room_id)
        assigned_faces.add(face_index)
    if len(assignments) != len(old_rooms):
        raise ValueError("Could not preserve room identity after wall move")
    return assignments


def _move_wall(plan: TopologyPlan, operation: dict[str, Any]) -> None:
    lineage_id = str(operation["wall_lineage_id"])
    lineage_walls = sorted(
        (
            wall
            for wall in plan.walls.values()
            if wall.lineage_id == lineage_id
        ),
        key=lambda wall: wall.lineage_start,
    )
    if not lineage_walls:
        raise ValueError(f"Wall lineage {lineage_id} does not exist")
    if any(wall.locked for wall in lineage_walls):
        raise ValueError(f"Wall lineage {lineage_id} is locked")

    start = lineage_walls[0].start
    end = lineage_walls[-1].end
    offset = float(operation["offset"])
    if abs(start[1] - end[1]) <= TOLERANCE:
        moved_start = (start[0], start[1] + offset)
        moved_end = (end[0], end[1] + offset)
    elif abs(start[0] - end[0]) <= TOLERANCE:
        moved_start = (start[0] + offset, start[1])
        moved_end = (end[0] + offset, end[1])
    else:
        raise ValueError("This V1 topology spike moves orthogonal walls only")

    moved_line = LineString([moved_start, moved_end])
    if (
        plan.footprint.boundary.distance(Point(moved_start)) > TOLERANCE
        or plan.footprint.boundary.distance(Point(moved_end)) > TOLERANCE
        or not plan.footprint.covers(moved_line)
    ):
        raise ValueError("Moved wall must remain inside the footprint with boundary endpoints")

    remaining = {
        wall_id: wall
        for wall_id, wall in plan.walls.items()
        if wall.lineage_id != lineage_id
    }
    remaining = _compact_wall_lineages(remaining)
    remaining[lineage_id] = WallSegment(
        id=lineage_id,
        lineage_id=lineage_id,
        start=moved_start,
        end=moved_end,
        lineage_start=0.0,
        lineage_end=moved_line.length,
    )
    plan.walls = _node_walls(remaining)
    derived_faces = _polygonized_faces(plan)
    plan.rooms = _assign_room_ids_by_overlap(plan.rooms, derived_faces)
    _remap_openings(plan)


def _validate_room_spans(plan: TopologyPlan) -> list[str]:
    errors: list[str] = []
    for room in plan.rooms.values():
        min_x, min_y, max_x, max_y = room.polygon.bounds
        minimum_span = min(max_x - min_x, max_y - min_y)
        if minimum_span < plan.minimum_safe_span:
            errors.append(
                f"Room {room.id} minimum span {minimum_span:.3f}m is below "
                f"the geometry safety limit {plan.minimum_safe_span:.3f}m"
            )
    return errors


def _validate_wall_network_coverage(plan: TopologyPlan) -> list[str]:
    derived_faces = _polygonized_faces(plan)
    if not derived_faces:
        return ["Wall network does not form closed faces across the footprint"]
    derived_union = unary_union(derived_faces)
    if derived_union.symmetric_difference(plan.footprint).area > TOLERANCE:
        return ["Wall network faces do not cover the complete footprint"]
    if len(derived_faces) != len(plan.rooms):
        return ["Wall network face count does not match stored rooms"]
    unmatched = list(derived_faces)
    for room in plan.rooms.values():
        match_index = next(
            (
                index
                for index, face in enumerate(unmatched)
                if face.symmetric_difference(room.polygon).area <= TOLERANCE
            ),
            None,
        )
        if match_index is None:
            return [f"Room {room.id} does not match a wall network face"]
        unmatched.pop(match_index)
    return []


def apply_topology_transaction(
    plan: TopologyPlan,
    operations: list[dict[str, Any]],
) -> TopologyResult:
    preview = deepcopy(plan)
    try:
        for operation in operations:
            operation_type = operation.get("type")
            if operation_type == "split_room":
                _split_room(preview, operation)
            elif operation_type == "merge_rooms":
                _merge_rooms(preview, operation)
            elif operation_type == "move_wall":
                _move_wall(preview, operation)
            else:
                raise ValueError("Unsupported topology operation")
    except (KeyError, TypeError, ValueError) as exc:
        return TopologyResult(False, plan, [str(exc)])
    validation_errors = [
        *_validate_wall_network_coverage(preview),
        *_validate_room_spans(preview),
    ]
    if validation_errors:
        return TopologyResult(False, plan, validation_errors)
    return TopologyResult(True, preview)
