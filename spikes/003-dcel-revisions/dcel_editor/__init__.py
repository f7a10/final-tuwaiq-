from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import math

from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union


@dataclass(frozen=True)
class Vertex:
    id: str
    x_mm: int
    y_mm: int


@dataclass(frozen=True)
class HalfEdge:
    id: str
    origin_vertex_id: str
    twin_id: str
    next_id: str
    prev_id: str
    face_id: str
    wall_run_id: str


@dataclass(frozen=True)
class Face:
    id: str
    edge_id: str
    kind: str


@dataclass(frozen=True)
class WallRun:
    id: str
    start_vertex_id: str
    end_vertex_id: str
    locked_support: bool = False
    allow_endpoint_slide: bool = False


@dataclass(frozen=True)
class Opening:
    id: str
    wall_run_id: str
    station_mm: int
    width_mm: int
    kind: str = "door"


@dataclass(frozen=True)
class PlanRevision:
    revision_id: str
    parent_id: str | None
    vertices: tuple[Vertex, ...]
    half_edges: tuple[HalfEdge, ...]
    faces: tuple[Face, ...]
    wall_runs: tuple[WallRun, ...]
    openings: tuple[Opening, ...]
    minimum_safe_span_mm: int = 800
    minimum_opening_edge_clearance_mm: int = 200
    operations: tuple[str, ...] = ()


@dataclass(frozen=True)
class RevisionResult:
    accepted: bool
    revision: PlanRevision
    errors: tuple[str, ...] = ()


def _canonical_payload(revision: PlanRevision) -> dict[str, object]:
    return {
        "parent_id": revision.parent_id,
        "vertices": [asdict(item) for item in sorted(revision.vertices, key=lambda item: item.id)],
        "half_edges": [
            asdict(item) for item in sorted(revision.half_edges, key=lambda item: item.id)
        ],
        "faces": [asdict(item) for item in sorted(revision.faces, key=lambda item: item.id)],
        "wall_runs": [
            asdict(item) for item in sorted(revision.wall_runs, key=lambda item: item.id)
        ],
        "openings": [
            asdict(item) for item in sorted(revision.openings, key=lambda item: item.id)
        ],
        "minimum_safe_span_mm": revision.minimum_safe_span_mm,
        "minimum_opening_edge_clearance_mm": revision.minimum_opening_edge_clearance_mm,
        "operations": list(revision.operations),
    }


def revision_hash(revision: PlanRevision) -> str:
    encoded = json.dumps(
        _canonical_payload(revision),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _edge(
    edge_id: str,
    origin: str,
    twin: str,
    next_id: str,
    prev_id: str,
    face: str,
    run: str,
) -> HalfEdge:
    return HalfEdge(edge_id, origin, twin, next_id, prev_id, face, run)


def make_two_room_revision() -> PlanRevision:
    vertices = (
        Vertex("v00", 0, 0),
        Vertex("v40", 4000, 0),
        Vertex("v80", 8000, 0),
        Vertex("v03", 0, 3000),
        Vertex("v43", 4000, 3000),
        Vertex("v83", 8000, 3000),
    )
    wall_runs = (
        WallRun("bottom-boundary", "v00", "v80", True, True),
        WallRun("right-boundary", "v80", "v83", True, False),
        WallRun("top-boundary", "v03", "v83", True, True),
        WallRun("left-boundary", "v00", "v03", True, False),
        WallRun("shared", "v40", "v43", False, False),
    )
    half_edges = (
        _edge("bl-left", "v00", "bl-ext", "shared-left", "left-left", "left", "bottom-boundary"),
        _edge("bl-ext", "v40", "bl-left", "left-ext", "br-ext", "exterior", "bottom-boundary"),
        _edge("br-right", "v40", "br-ext", "right-right", "shared-right", "right", "bottom-boundary"),
        _edge("br-ext", "v80", "br-right", "bl-ext", "right-ext", "exterior", "bottom-boundary"),
        _edge("right-right", "v80", "right-ext", "tr-right", "br-right", "right", "right-boundary"),
        _edge("right-ext", "v83", "right-right", "br-ext", "tr-ext", "exterior", "right-boundary"),
        _edge("tr-right", "v83", "tr-ext", "shared-right", "right-right", "right", "top-boundary"),
        _edge("tr-ext", "v43", "tr-right", "right-ext", "tl-ext", "exterior", "top-boundary"),
        _edge("tl-left", "v43", "tl-ext", "left-left", "shared-left", "left", "top-boundary"),
        _edge("tl-ext", "v03", "tl-left", "tr-ext", "left-ext", "exterior", "top-boundary"),
        _edge("left-left", "v03", "left-ext", "bl-left", "tl-left", "left", "left-boundary"),
        _edge("left-ext", "v00", "left-left", "tl-ext", "bl-ext", "exterior", "left-boundary"),
        _edge("shared-left", "v40", "shared-right", "tl-left", "bl-left", "left", "shared"),
        _edge("shared-right", "v43", "shared-left", "br-right", "tr-right", "right", "shared"),
    )
    faces = (
        Face("left", "bl-left", "room"),
        Face("right", "br-right", "room"),
        Face("exterior", "bl-ext", "exterior"),
    )
    openings = (
        Opening("entrance", "left-boundary", 1500, 900),
        Opening("shared-door", "shared", 1500, 900),
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=None,
        vertices=vertices,
        half_edges=half_edges,
        faces=faces,
        wall_runs=wall_runs,
        openings=openings,
    )
    return replace(draft, revision_id=revision_hash(draft))


def _duplicate_ids(items: tuple[object, ...]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        item_id = getattr(item, "id")
        if item_id in seen:
            duplicates.add(item_id)
        seen.add(item_id)
    return duplicates


def _face_cycle(
    face: Face,
    edge_map: dict[str, HalfEdge],
) -> tuple[list[HalfEdge], str | None]:
    if face.edge_id not in edge_map:
        return [], f"Face {face.id} references missing edge {face.edge_id}"
    cycle: list[HalfEdge] = []
    current_id = face.edge_id
    visited: set[str] = set()
    for _ in range(len(edge_map) + 1):
        if current_id in visited:
            if current_id == face.edge_id:
                return cycle, None
            return cycle, f"Face {face.id} cycle repeats edge {current_id} before closing"
        if current_id not in edge_map:
            return cycle, f"Face {face.id} cycle references missing edge {current_id}"
        edge = edge_map[current_id]
        if edge.face_id != face.id:
            return cycle, f"Half-edge {edge.id} belongs to face {edge.face_id}, not {face.id}"
        visited.add(current_id)
        cycle.append(edge)
        current_id = edge.next_id
    return cycle, f"Face {face.id} cycle does not close"


def _face_polygon_geometry(
    revision: PlanRevision,
    face: Face,
) -> Polygon:
    edge_map = {edge.id: edge for edge in revision.half_edges}
    vertex_map = {vertex.id: vertex for vertex in revision.vertices}
    cycle, error = _face_cycle(face, edge_map)
    if error:
        raise ValueError(error)
    return Polygon(
        [
            (
                vertex_map[edge.origin_vertex_id].x_mm,
                vertex_map[edge.origin_vertex_id].y_mm,
            )
            for edge in cycle
        ]
    )


def _validate_geometry_differential(revision: PlanRevision) -> list[str]:
    errors: list[str] = []
    exterior_face = next(face for face in revision.faces if face.kind == "exterior")
    footprint = _face_polygon_geometry(revision, exterior_face)
    if not footprint.is_valid or footprint.area <= 0:
        return ["Exterior footprint geometry is invalid"]

    room_polygons = [
        _face_polygon_geometry(revision, face)
        for face in revision.faces
        if face.kind == "room"
    ]
    for face, polygon in zip(
        (face for face in revision.faces if face.kind == "room"),
        room_polygons,
    ):
        if not polygon.is_valid or polygon.area <= 0:
            errors.append(f"Room face {face.id} geometry is invalid")
        elif not footprint.covers(polygon):
            errors.append(f"Room face {face.id} lies outside the footprint")
        else:
            min_x, min_y, max_x, max_y = polygon.bounds
            minimum_span = min(max_x - min_x, max_y - min_y)
            if minimum_span < revision.minimum_safe_span_mm:
                errors.append(
                    f"Room face {face.id} minimum span {minimum_span:.0f}mm is below "
                    f"the geometry safety limit {revision.minimum_safe_span_mm}mm"
                )
    if errors:
        return errors

    room_union = unary_union(room_polygons)
    if room_union.symmetric_difference(footprint).area > 1.0:
        errors.append("DCEL room faces do not form the complete footprint partition")

    vertex_map = {vertex.id: vertex for vertex in revision.vertices}
    wall_lines = []
    for wall_run in revision.wall_runs:
        start = vertex_map[wall_run.start_vertex_id]
        end = vertex_map[wall_run.end_vertex_id]
        wall_lines.append(
            LineString([(start.x_mm, start.y_mm), (end.x_mm, end.y_mm)])
        )
    polygonized_faces = [
        polygon
        for polygon in polygonize(unary_union(wall_lines))
        if footprint.covers(polygon.representative_point())
    ]
    unmatched = list(polygonized_faces)
    for room_polygon in room_polygons:
        match_index = next(
            (
                index
                for index, polygon in enumerate(unmatched)
                if polygon.symmetric_difference(room_polygon).area <= 1.0
            ),
            None,
        )
        if match_index is None:
            errors.append("DCEL face geometry differs from polygonized wall geometry")
            break
        unmatched.pop(match_index)
    if unmatched:
        errors.append("Polygonized wall geometry contains unexpected bounded faces")
    return errors


def _validate_reachability(revision: PlanRevision) -> list[str]:
    edge_map = {edge.id: edge for edge in revision.half_edges}
    vertex_map = {vertex.id: vertex for vertex in revision.vertices}
    run_map = {run.id: run for run in revision.wall_runs}
    face_map = {face.id: face for face in revision.faces}
    graph: dict[str, set[str]] = {face_id: set() for face_id in face_map}
    errors: list[str] = []

    for opening in revision.openings:
        if opening.kind != "door":
            continue
        wall_run = run_map[opening.wall_run_id]
        run_start = vertex_map[wall_run.start_vertex_id]
        run_end = vertex_map[wall_run.end_vertex_id]
        support_x = run_end.x_mm - run_start.x_mm
        support_y = run_end.y_mm - run_start.y_mm
        support_length = math.hypot(support_x, support_y)
        candidate_face_pairs: set[frozenset[str]] = set()
        visited_pairs: set[frozenset[str]] = set()
        for edge in revision.half_edges:
            if edge.wall_run_id != wall_run.id:
                continue
            twin = edge_map[edge.twin_id]
            edge_pair = frozenset((edge.id, twin.id))
            if edge_pair in visited_pairs:
                continue
            visited_pairs.add(edge_pair)
            first = vertex_map[edge.origin_vertex_id]
            second = vertex_map[twin.origin_vertex_id]

            def station(vertex: Vertex) -> float:
                return (
                    support_x * (vertex.x_mm - run_start.x_mm)
                    + support_y * (vertex.y_mm - run_start.y_mm)
                ) / support_length

            first_station = station(first)
            second_station = station(second)
            if (
                min(first_station, second_station) - 0.001
                <= opening.station_mm
                <= max(first_station, second_station) + 0.001
            ):
                candidate_face_pairs.add(frozenset((edge.face_id, twin.face_id)))
        if len(candidate_face_pairs) != 1:
            errors.append(
                f"Door {opening.id} is not hosted by exactly one unambiguous face pair"
            )
            continue
        face_pair = next(iter(candidate_face_pairs))
        if len(face_pair) != 2:
            errors.append(f"Door {opening.id} does not connect two distinct faces")
            continue
        first_face, second_face = tuple(face_pair)
        graph[first_face].add(second_face)
        graph[second_face].add(first_face)

    exterior_faces = [face.id for face in revision.faces if face.kind == "exterior"]
    if len(exterior_faces) != 1:
        return errors
    reached = {exterior_faces[0]}
    frontier = [exterior_faces[0]]
    while frontier:
        current = frontier.pop()
        for neighbor in graph[current] - reached:
            reached.add(neighbor)
            frontier.append(neighbor)
    unreachable_rooms = sorted(
        face.id
        for face in revision.faces
        if face.kind == "room" and face.id not in reached
    )
    if unreachable_rooms:
        errors.append(
            "Unreachable room faces from exterior entrance: "
            + ", ".join(unreachable_rooms)
        )
    return errors


def face_area_m2(revision: PlanRevision, face_id: str) -> float:
    edge_map = {edge.id: edge for edge in revision.half_edges}
    vertex_map = {vertex.id: vertex for vertex in revision.vertices}
    face_map = {face.id: face for face in revision.faces}
    cycle, error = _face_cycle(face_map[face_id], edge_map)
    if error:
        raise ValueError(error)
    coordinates = [
        (
            vertex_map[edge.origin_vertex_id].x_mm,
            vertex_map[edge.origin_vertex_id].y_mm,
        )
        for edge in cycle
    ]
    twice_area = sum(
        first_x * second_y - second_x * first_y
        for (first_x, first_y), (second_x, second_y) in zip(
            coordinates,
            coordinates[1:] + coordinates[:1],
        )
    )
    return abs(twice_area) / 2_000_000


def opening_segment_mm(
    revision: PlanRevision,
    opening_id: str,
) -> tuple[tuple[float, float], tuple[float, float]]:
    opening = next(item for item in revision.openings if item.id == opening_id)
    wall_run = next(item for item in revision.wall_runs if item.id == opening.wall_run_id)
    vertex_map = {vertex.id: vertex for vertex in revision.vertices}
    start = vertex_map[wall_run.start_vertex_id]
    end = vertex_map[wall_run.end_vertex_id]
    length = math.hypot(end.x_mm - start.x_mm, end.y_mm - start.y_mm)
    unit_x = (end.x_mm - start.x_mm) / length
    unit_y = (end.y_mm - start.y_mm) / length
    center_x = start.x_mm + unit_x * opening.station_mm
    center_y = start.y_mm + unit_y * opening.station_mm
    half_width = opening.width_mm / 2
    return (
        (center_x - unit_x * half_width, center_y - unit_y * half_width),
        (center_x + unit_x * half_width, center_y + unit_y * half_width),
    )


def _point_stays_on_support(
    old_vertex: Vertex,
    new_vertex: Vertex,
    support_start: Vertex,
    support_end: Vertex,
) -> bool:
    support_x = support_end.x_mm - support_start.x_mm
    support_y = support_end.y_mm - support_start.y_mm
    point_x = new_vertex.x_mm - support_start.x_mm
    point_y = new_vertex.y_mm - support_start.y_mm
    cross_product = support_x * point_y - support_y * point_x
    return cross_product == 0 and old_vertex.id == new_vertex.id


def apply_node_wall_run(
    base: PlanRevision,
    *,
    base_revision_id: str,
    wall_run_id: str,
    station_mm: int,
    vertex_id: str,
) -> RevisionResult:
    if base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    base_errors = validate_dcel(base)
    if base_errors:
        return RevisionResult(False, base, tuple(base_errors))
    if any(vertex.id == vertex_id for vertex in base.vertices):
        return RevisionResult(False, base, (f"Vertex ID {vertex_id} already exists",))

    run = next((item for item in base.wall_runs if item.id == wall_run_id), None)
    if run is None:
        return RevisionResult(False, base, (f"Wall run {wall_run_id} does not exist",))
    vertex_map = {vertex.id: vertex for vertex in base.vertices}
    start = vertex_map[run.start_vertex_id]
    end = vertex_map[run.end_vertex_id]
    run_length = round(math.hypot(end.x_mm - start.x_mm, end.y_mm - start.y_mm))
    station_mm = int(station_mm)
    if not 0 < station_mm < run_length:
        return RevisionResult(
            False,
            base,
            (f"Node station must be inside wall run {wall_run_id}",),
        )
    if start.y_mm == end.y_mm:
        direction = 1 if end.x_mm > start.x_mm else -1
        node = Vertex(vertex_id, start.x_mm + direction * station_mm, start.y_mm)
    elif start.x_mm == end.x_mm:
        direction = 1 if end.y_mm > start.y_mm else -1
        node = Vertex(vertex_id, start.x_mm, start.y_mm + direction * station_mm)
    else:
        return RevisionResult(False, base, ("V1 nodes orthogonal wall runs only",))
    if any(
        (vertex.x_mm, vertex.y_mm) == (node.x_mm, node.y_mm)
        for vertex in base.vertices
    ):
        return RevisionResult(False, base, ("Wall run is already noded at that station",))

    edge_map = {edge.id: edge for edge in base.half_edges}
    containing_pairs: list[tuple[HalfEdge, HalfEdge]] = []
    visited_pairs: set[frozenset[str]] = set()
    for edge in base.half_edges:
        if edge.wall_run_id != wall_run_id:
            continue
        twin = edge_map[edge.twin_id]
        pair_key = frozenset((edge.id, twin.id))
        if pair_key in visited_pairs:
            continue
        visited_pairs.add(pair_key)
        first = vertex_map[edge.origin_vertex_id]
        second = vertex_map[twin.origin_vertex_id]
        segment_x = second.x_mm - first.x_mm
        segment_y = second.y_mm - first.y_mm
        node_x = node.x_mm - first.x_mm
        node_y = node.y_mm - first.y_mm
        cross_product = segment_x * node_y - segment_y * node_x
        station_numerator = segment_x * node_x + segment_y * node_y
        segment_length_squared = segment_x * segment_x + segment_y * segment_y
        if cross_product == 0 and 0 < station_numerator < segment_length_squared:
            containing_pairs.append((edge, twin))
    if len(containing_pairs) != 1:
        return RevisionResult(
            False,
            base,
            ("Node station must lie inside exactly one wall segment",),
        )

    first_edge, second_edge = containing_pairs[0]
    support_x = end.x_mm - start.x_mm
    support_y = end.y_mm - start.y_mm

    def run_station_numerator(edge: HalfEdge) -> int:
        origin = vertex_map[edge.origin_vertex_id]
        return support_x * (origin.x_mm - start.x_mm) + support_y * (
            origin.y_mm - start.y_mm
        )

    if run_station_numerator(first_edge) < run_station_numerator(second_edge):
        forward_edge, reverse_edge = first_edge, second_edge
    else:
        forward_edge, reverse_edge = second_edge, first_edge
    old_reverse_origin = reverse_edge.origin_vertex_id
    new_forward_id = f"{forward_edge.id}@{vertex_id}"
    new_reverse_id = f"{reverse_edge.id}@{vertex_id}"
    if new_forward_id in edge_map or new_reverse_id in edge_map:
        return RevisionResult(False, base, ("Generated noded half-edge IDs already exist",))

    preserved_forward = replace(forward_edge, next_id=new_forward_id)
    preserved_reverse = replace(
        reverse_edge,
        origin_vertex_id=vertex_id,
        prev_id=new_reverse_id,
    )
    new_forward = HalfEdge(
        id=new_forward_id,
        origin_vertex_id=vertex_id,
        twin_id=new_reverse_id,
        next_id=forward_edge.next_id,
        prev_id=forward_edge.id,
        face_id=forward_edge.face_id,
        wall_run_id=wall_run_id,
    )
    new_reverse = HalfEdge(
        id=new_reverse_id,
        origin_vertex_id=old_reverse_origin,
        twin_id=new_forward_id,
        next_id=reverse_edge.id,
        prev_id=reverse_edge.prev_id,
        face_id=reverse_edge.face_id,
        wall_run_id=wall_run_id,
    )
    updates = {
        forward_edge.id: preserved_forward,
        reverse_edge.id: preserved_reverse,
        forward_edge.next_id: replace(
            edge_map[forward_edge.next_id],
            prev_id=new_forward_id,
        ),
        reverse_edge.prev_id: replace(
            edge_map[reverse_edge.prev_id],
            next_id=new_reverse_id,
        ),
    }
    noded_edges = tuple(
        updates.get(edge.id, edge) for edge in base.half_edges
    ) + (new_forward, new_reverse)
    command = json.dumps(
        {
            "type": "node_wall_run",
            "wall_run_id": wall_run_id,
            "station_mm": station_mm,
            "vertex_id": vertex_id,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=base.revision_id,
        vertices=base.vertices + (node,),
        half_edges=noded_edges,
        faces=base.faces,
        wall_runs=base.wall_runs,
        openings=base.openings,
        minimum_safe_span_mm=base.minimum_safe_span_mm,
        minimum_opening_edge_clearance_mm=base.minimum_opening_edge_clearance_mm,
        operations=base.operations + (command,),
    )
    noded = replace(draft, revision_id=revision_hash(draft))
    noded_errors = validate_dcel(noded)
    if noded_errors:
        return RevisionResult(False, base, tuple(noded_errors))
    return RevisionResult(True, noded)


def apply_split_face(
    base: PlanRevision,
    *,
    base_revision_id: str,
    face_id: str,
    start_vertex_id: str,
    end_vertex_id: str,
    new_face_id: str,
    wall_run_id: str,
    opening: Opening | None = None,
) -> RevisionResult:
    if base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    base_errors = validate_dcel(base)
    if base_errors:
        return RevisionResult(False, base, tuple(base_errors))

    face_map = {face.id: face for face in base.faces}
    face = face_map.get(face_id)
    if face is None or face.kind != "room":
        return RevisionResult(False, base, (f"Room face {face_id} does not exist",))
    if new_face_id in face_map:
        return RevisionResult(False, base, (f"Face ID {new_face_id} already exists",))
    if any(run.id == wall_run_id for run in base.wall_runs):
        return RevisionResult(False, base, (f"Wall run ID {wall_run_id} already exists",))
    vertex_ids = {vertex.id for vertex in base.vertices}
    if start_vertex_id == end_vertex_id or not {
        start_vertex_id,
        end_vertex_id,
    }.issubset(vertex_ids):
        return RevisionResult(False, base, ("Split endpoints must be distinct existing vertices",))
    if any(
        {run.start_vertex_id, run.end_vertex_id}
        == {start_vertex_id, end_vertex_id}
        for run in base.wall_runs
    ):
        return RevisionResult(False, base, ("A wall already connects the split endpoints",))
    if opening is not None:
        if opening.wall_run_id != wall_run_id:
            return RevisionResult(False, base, ("Opening must reference the new wall run",))
        if any(item.id == opening.id for item in base.openings):
            return RevisionResult(False, base, (f"Opening ID {opening.id} already exists",))

    edge_map = {edge.id: edge for edge in base.half_edges}
    cycle, cycle_error = _face_cycle(face, edge_map)
    if cycle_error:
        return RevisionResult(False, base, (cycle_error,))
    origins = [edge.origin_vertex_id for edge in cycle]
    if origins.count(start_vertex_id) != 1 or origins.count(end_vertex_id) != 1:
        return RevisionResult(
            False,
            base,
            ("Split endpoints must each occur once on the selected face boundary",),
        )
    start_index = origins.index(start_vertex_id)
    end_index = origins.index(end_vertex_id)

    def cycle_slice(first: int, last: int) -> list[HalfEdge]:
        if first < last:
            return cycle[first:last]
        return cycle[first:] + cycle[:last]

    start_to_end = cycle_slice(start_index, end_index)
    end_to_start = cycle_slice(end_index, start_index)
    if len(start_to_end) < 2 or len(end_to_start) < 2:
        return RevisionResult(
            False,
            base,
            ("Split would duplicate a boundary edge or create a degenerate face",),
        )

    survivor_edge_id = f"{wall_run_id}-survivor"
    new_face_edge_id = f"{wall_run_id}-new-face"
    if survivor_edge_id in edge_map or new_face_edge_id in edge_map:
        return RevisionResult(False, base, ("Generated half-edge IDs already exist",))
    survivor_edge = HalfEdge(
        id=survivor_edge_id,
        origin_vertex_id=start_vertex_id,
        twin_id=new_face_edge_id,
        next_id=end_to_start[0].id,
        prev_id=end_to_start[-1].id,
        face_id=face_id,
        wall_run_id=wall_run_id,
    )
    new_face_edge = HalfEdge(
        id=new_face_edge_id,
        origin_vertex_id=end_vertex_id,
        twin_id=survivor_edge_id,
        next_id=start_to_end[0].id,
        prev_id=start_to_end[-1].id,
        face_id=new_face_id,
        wall_run_id=wall_run_id,
    )

    updates: dict[str, HalfEdge] = {}
    for edge in start_to_end:
        updates[edge.id] = replace(edge, face_id=new_face_id)
    for edge in end_to_start:
        updates[edge.id] = replace(edge, face_id=face_id)
    updates[start_to_end[0].id] = replace(
        updates[start_to_end[0].id],
        prev_id=new_face_edge.id,
    )
    updates[start_to_end[-1].id] = replace(
        updates[start_to_end[-1].id],
        next_id=new_face_edge.id,
    )
    updates[end_to_start[0].id] = replace(
        updates[end_to_start[0].id],
        prev_id=survivor_edge.id,
    )
    updates[end_to_start[-1].id] = replace(
        updates[end_to_start[-1].id],
        next_id=survivor_edge.id,
    )
    split_edges = tuple(
        updates.get(edge.id, edge) for edge in base.half_edges
    ) + (survivor_edge, new_face_edge)
    split_faces = tuple(
        replace(item, edge_id=end_to_start[0].id) if item.id == face_id else item
        for item in base.faces
    ) + (Face(new_face_id, start_to_end[0].id, "room"),)
    split_openings = base.openings + ((opening,) if opening is not None else ())
    command = json.dumps(
        {
            "type": "split_face",
            "face_id": face_id,
            "new_face_id": new_face_id,
            "wall_run_id": wall_run_id,
            "start_vertex_id": start_vertex_id,
            "end_vertex_id": end_vertex_id,
            "opening": asdict(opening) if opening is not None else None,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=base.revision_id,
        vertices=base.vertices,
        half_edges=split_edges,
        faces=split_faces,
        wall_runs=base.wall_runs
        + (WallRun(wall_run_id, start_vertex_id, end_vertex_id),),
        openings=split_openings,
        minimum_safe_span_mm=base.minimum_safe_span_mm,
        minimum_opening_edge_clearance_mm=base.minimum_opening_edge_clearance_mm,
        operations=base.operations + (command,),
    )
    split = replace(draft, revision_id=revision_hash(draft))
    split_errors = validate_dcel(split)
    if split_errors:
        return RevisionResult(False, base, tuple(split_errors))
    return RevisionResult(True, split)


def apply_split_face_by_wall_stations(
    base: PlanRevision,
    *,
    base_revision_id: str,
    face_id: str,
    first_wall_run_id: str,
    first_station_mm: int,
    first_vertex_id: str,
    second_wall_run_id: str,
    second_station_mm: int,
    second_vertex_id: str,
    new_face_id: str,
    partition_wall_run_id: str,
    opening: Opening | None = None,
) -> RevisionResult:
    if base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    base_errors = validate_dcel(base)
    if base_errors:
        return RevisionResult(False, base, tuple(base_errors))

    first_node = apply_node_wall_run(
        base,
        base_revision_id=base.revision_id,
        wall_run_id=first_wall_run_id,
        station_mm=first_station_mm,
        vertex_id=first_vertex_id,
    )
    if not first_node.accepted:
        return RevisionResult(
            False,
            base,
            tuple(f"First split endpoint: {error}" for error in first_node.errors),
        )
    second_node = apply_node_wall_run(
        first_node.revision,
        base_revision_id=first_node.revision.revision_id,
        wall_run_id=second_wall_run_id,
        station_mm=second_station_mm,
        vertex_id=second_vertex_id,
    )
    if not second_node.accepted:
        return RevisionResult(
            False,
            base,
            tuple(f"Second split endpoint: {error}" for error in second_node.errors),
        )
    split_result = apply_split_face(
        second_node.revision,
        base_revision_id=second_node.revision.revision_id,
        face_id=face_id,
        start_vertex_id=first_vertex_id,
        end_vertex_id=second_vertex_id,
        new_face_id=new_face_id,
        wall_run_id=partition_wall_run_id,
        opening=opening,
    )
    if not split_result.accepted:
        return RevisionResult(
            False,
            base,
            tuple(f"Partition: {error}" for error in split_result.errors),
        )

    intermediate = split_result.revision
    command = json.dumps(
        {
            "type": "split_face_by_wall_stations",
            "face_id": face_id,
            "first_wall_run_id": first_wall_run_id,
            "first_station_mm": int(first_station_mm),
            "first_vertex_id": first_vertex_id,
            "second_wall_run_id": second_wall_run_id,
            "second_station_mm": int(second_station_mm),
            "second_vertex_id": second_vertex_id,
            "new_face_id": new_face_id,
            "partition_wall_run_id": partition_wall_run_id,
            "opening": asdict(opening) if opening is not None else None,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=base.revision_id,
        vertices=intermediate.vertices,
        half_edges=intermediate.half_edges,
        faces=intermediate.faces,
        wall_runs=intermediate.wall_runs,
        openings=intermediate.openings,
        minimum_safe_span_mm=base.minimum_safe_span_mm,
        minimum_opening_edge_clearance_mm=base.minimum_opening_edge_clearance_mm,
        operations=base.operations + (command,),
    )
    atomic_split = replace(draft, revision_id=revision_hash(draft))
    atomic_errors = validate_dcel(atomic_split)
    if atomic_errors:
        return RevisionResult(False, base, tuple(atomic_errors))
    return RevisionResult(True, atomic_split)


def apply_merge_faces(
    base: PlanRevision,
    *,
    base_revision_id: str,
    partition_wall_run_id: str,
    survivor_face_id: str,
    opening_disposition: str | None = None,
) -> RevisionResult:
    if base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    base_errors = validate_dcel(base)
    if base_errors:
        return RevisionResult(False, base, tuple(base_errors))
    wall_run = next(
        (run for run in base.wall_runs if run.id == partition_wall_run_id),
        None,
    )
    if wall_run is None:
        return RevisionResult(
            False,
            base,
            (f"Partition wall run {partition_wall_run_id} does not exist",),
        )
    if not any(face.id == survivor_face_id for face in base.faces):
        return RevisionResult(
            False,
            base,
            (f"Survivor face {survivor_face_id} does not exist",),
        )
    hosted_openings = [
        opening
        for opening in base.openings
        if opening.wall_run_id == partition_wall_run_id
    ]
    if hosted_openings and opening_disposition is None:
        return RevisionResult(
            False,
            base,
            ("Explicit opening disposition is required before removing the partition",),
        )
    if opening_disposition not in (None, "remove"):
        return RevisionResult(
            False,
            base,
            (f"Unsupported opening disposition {opening_disposition}",),
        )
    if wall_run.locked_support:
        return RevisionResult(
            False,
            base,
            (f"Partition wall run {partition_wall_run_id} is locked",),
        )

    partition_edges = [
        edge for edge in base.half_edges if edge.wall_run_id == partition_wall_run_id
    ]
    if len(partition_edges) != 2:
        return RevisionResult(
            False,
            base,
            ("Partition wall must have exactly two half-edges",),
        )
    adjacent_face_ids = {edge.face_id for edge in partition_edges}
    if len(adjacent_face_ids) != 2 or survivor_face_id not in adjacent_face_ids:
        return RevisionResult(
            False,
            base,
            ("Partition wall must separate the survivor from one other face",),
        )
    face_map = {face.id: face for face in base.faces}
    if any(face_map[face_id].kind != "room" for face_id in adjacent_face_ids):
        return RevisionResult(
            False,
            base,
            ("Only a partition between two room faces can be merged",),
        )

    removed_face_id = next(
        face_id for face_id in adjacent_face_ids if face_id != survivor_face_id
    )
    survivor_partition_edge = next(
        edge for edge in partition_edges if edge.face_id == survivor_face_id
    )
    removed_partition_edge = next(
        edge for edge in partition_edges if edge.face_id == removed_face_id
    )
    edge_map = {edge.id: edge for edge in base.half_edges}
    survivor_prev = edge_map[survivor_partition_edge.prev_id]
    survivor_next = edge_map[survivor_partition_edge.next_id]
    removed_prev = edge_map[removed_partition_edge.prev_id]
    removed_next = edge_map[removed_partition_edge.next_id]

    rewired = {
        survivor_prev.id: replace(survivor_prev, next_id=removed_next.id),
        removed_next.id: replace(removed_next, prev_id=survivor_prev.id),
        removed_prev.id: replace(removed_prev, next_id=survivor_next.id),
        survivor_next.id: replace(survivor_next, prev_id=removed_prev.id),
    }
    removed_edge_ids = {edge.id for edge in partition_edges}
    merged_edges: list[HalfEdge] = []
    for edge in base.half_edges:
        if edge.id in removed_edge_ids:
            continue
        merged_edge = rewired.get(edge.id, edge)
        if merged_edge.face_id == removed_face_id:
            merged_edge = replace(merged_edge, face_id=survivor_face_id)
        merged_edges.append(merged_edge)

    merged_faces = tuple(
        replace(face, edge_id=survivor_prev.id)
        if face.id == survivor_face_id
        else face
        for face in base.faces
        if face.id != removed_face_id
    )
    merged_openings = tuple(
        opening
        for opening in base.openings
        if opening.wall_run_id != partition_wall_run_id
    )
    command = json.dumps(
        {
            "type": "merge_faces",
            "partition_wall_run_id": partition_wall_run_id,
            "survivor_face_id": survivor_face_id,
            "opening_disposition": opening_disposition,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=base.revision_id,
        vertices=base.vertices,
        half_edges=tuple(merged_edges),
        faces=merged_faces,
        wall_runs=tuple(
            run for run in base.wall_runs if run.id != partition_wall_run_id
        ),
        openings=merged_openings,
        minimum_safe_span_mm=base.minimum_safe_span_mm,
        minimum_opening_edge_clearance_mm=base.minimum_opening_edge_clearance_mm,
        operations=base.operations + (command,),
    )
    merged = replace(draft, revision_id=revision_hash(draft))
    merged_errors = validate_dcel(merged)
    if merged_errors:
        return RevisionResult(False, base, tuple(merged_errors))
    return RevisionResult(True, merged)


def apply_add_opening(
    base: PlanRevision,
    *,
    base_revision_id: str,
    opening: Opening,
) -> RevisionResult:
    if base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    base_errors = validate_dcel(base)
    if base_errors:
        return RevisionResult(False, base, tuple(base_errors))
    if any(item.id == opening.id for item in base.openings):
        return RevisionResult(False, base, (f"Opening ID {opening.id} already exists",))
    command = json.dumps(
        {
            "type": "add_opening",
            "opening": asdict(opening),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=base.revision_id,
        vertices=base.vertices,
        half_edges=base.half_edges,
        faces=base.faces,
        wall_runs=base.wall_runs,
        openings=base.openings + (opening,),
        minimum_safe_span_mm=base.minimum_safe_span_mm,
        minimum_opening_edge_clearance_mm=base.minimum_opening_edge_clearance_mm,
        operations=base.operations + (command,),
    )
    added = replace(draft, revision_id=revision_hash(draft))
    added_errors = validate_dcel(added)
    if added_errors:
        return RevisionResult(False, base, tuple(added_errors))
    return RevisionResult(True, added)


def apply_remove_opening(
    base: PlanRevision,
    *,
    base_revision_id: str,
    opening_id: str,
) -> RevisionResult:
    if base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    base_errors = validate_dcel(base)
    if base_errors:
        return RevisionResult(False, base, tuple(base_errors))
    if not any(item.id == opening_id for item in base.openings):
        return RevisionResult(False, base, (f"Opening {opening_id} does not exist",))
    command = json.dumps(
        {
            "type": "remove_opening",
            "opening_id": opening_id,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=base.revision_id,
        vertices=base.vertices,
        half_edges=base.half_edges,
        faces=base.faces,
        wall_runs=base.wall_runs,
        openings=tuple(
            item for item in base.openings if item.id != opening_id
        ),
        minimum_safe_span_mm=base.minimum_safe_span_mm,
        minimum_opening_edge_clearance_mm=base.minimum_opening_edge_clearance_mm,
        operations=base.operations + (command,),
    )
    removed = replace(draft, revision_id=revision_hash(draft))
    removed_errors = validate_dcel(removed)
    if removed_errors:
        return RevisionResult(False, base, tuple(removed_errors))
    return RevisionResult(True, removed)


def apply_move_opening(
    base: PlanRevision,
    *,
    base_revision_id: str,
    opening_id: str,
    station_mm: int,
) -> RevisionResult:
    if base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    base_errors = validate_dcel(base)
    if base_errors:
        return RevisionResult(False, base, tuple(base_errors))
    opening = next((item for item in base.openings if item.id == opening_id), None)
    if opening is None:
        return RevisionResult(False, base, (f"Opening {opening_id} does not exist",))
    station_mm = int(station_mm)
    if opening.station_mm == station_mm:
        return RevisionResult(False, base, ("Unchanged opening station is a no-op",))
    moved_opening = replace(opening, station_mm=station_mm)
    command = json.dumps(
        {
            "type": "move_opening",
            "opening_id": opening_id,
            "station_mm": station_mm,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=base.revision_id,
        vertices=base.vertices,
        half_edges=base.half_edges,
        faces=base.faces,
        wall_runs=base.wall_runs,
        openings=tuple(
            moved_opening if item.id == opening_id else item
            for item in base.openings
        ),
        minimum_safe_span_mm=base.minimum_safe_span_mm,
        minimum_opening_edge_clearance_mm=base.minimum_opening_edge_clearance_mm,
        operations=base.operations + (command,),
    )
    moved = replace(draft, revision_id=revision_hash(draft))
    moved_errors = validate_dcel(moved)
    if moved_errors:
        return RevisionResult(False, base, tuple(moved_errors))
    return RevisionResult(True, moved)


def apply_move_wall(
    base: PlanRevision,
    *,
    base_revision_id: str,
    wall_run_id: str,
    offset_mm: int,
) -> RevisionResult:
    if base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    offset_mm = int(offset_mm)
    if offset_mm == 0:
        return RevisionResult(False, base, ("Zero-distance wall move is a no-op",))
    base_errors = validate_dcel(base)
    if base_errors:
        return RevisionResult(False, base, tuple(base_errors))

    run_map = {run.id: run for run in base.wall_runs}
    target = run_map.get(wall_run_id)
    if target is None:
        return RevisionResult(False, base, (f"Wall run {wall_run_id} does not exist",))
    if target.locked_support:
        return RevisionResult(False, base, (f"Wall run {wall_run_id} is locked",))

    vertex_map = {vertex.id: vertex for vertex in base.vertices}
    start = vertex_map[target.start_vertex_id]
    end = vertex_map[target.end_vertex_id]
    if start.x_mm == end.x_mm:
        moved_start = replace(start, x_mm=start.x_mm + int(offset_mm))
        moved_end = replace(end, x_mm=end.x_mm + int(offset_mm))
    elif start.y_mm == end.y_mm:
        moved_start = replace(start, y_mm=start.y_mm + int(offset_mm))
        moved_end = replace(end, y_mm=end.y_mm + int(offset_mm))
    else:
        return RevisionResult(False, base, ("V1 moves orthogonal wall runs only",))

    moved_vertices = {
        moved_start.id: moved_start,
        moved_end.id: moved_end,
    }
    for support in base.wall_runs:
        if support.id == target.id or not support.locked_support:
            continue
        support_vertices = {
            edge.origin_vertex_id
            for edge in base.half_edges
            if edge.wall_run_id == support.id
        }
        affected = support_vertices.intersection(moved_vertices)
        if not affected:
            continue
        if not support.allow_endpoint_slide:
            return RevisionResult(
                False,
                base,
                (f"Wall run {target.id} endpoint is fixed by {support.id}",),
            )
        support_start = vertex_map[support.start_vertex_id]
        support_end = vertex_map[support.end_vertex_id]
        for vertex_id in affected:
            if not _point_stays_on_support(
                vertex_map[vertex_id],
                moved_vertices[vertex_id],
                support_start,
                support_end,
            ):
                return RevisionResult(
                    False,
                    base,
                    (f"Wall run {target.id} leaves locked support {support.id}",),
                )

    updated_vertices = tuple(
        moved_vertices.get(vertex.id, vertex) for vertex in base.vertices
    )
    command = json.dumps(
        {
            "type": "move_wall",
            "wall_run_id": wall_run_id,
            "offset_mm": int(offset_mm),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=base.revision_id,
        vertices=updated_vertices,
        half_edges=base.half_edges,
        faces=base.faces,
        wall_runs=base.wall_runs,
        openings=base.openings,
        minimum_safe_span_mm=base.minimum_safe_span_mm,
        minimum_opening_edge_clearance_mm=base.minimum_opening_edge_clearance_mm,
        operations=base.operations + (command,),
    )
    child = replace(draft, revision_id=revision_hash(draft))
    child_errors = validate_dcel(child)
    if child_errors:
        return RevisionResult(False, base, tuple(child_errors))
    return RevisionResult(True, child)


def apply_transaction(
    base: PlanRevision,
    *,
    base_revision_id: str,
    commands: tuple[dict[str, object], ...],
) -> RevisionResult:
    if base_revision_id != base.revision_id:
        return RevisionResult(False, base, ("Stale base revision",))
    base_errors = validate_dcel(base)
    if base_errors:
        return RevisionResult(False, base, tuple(base_errors))
    if not commands:
        return RevisionResult(False, base, ("Empty transaction is a no-op",))

    working = base
    for operation_index, command in enumerate(commands, start=1):
        command_type = command.get("type")
        if command_type == "move_opening":
            result = apply_move_opening(
                working,
                base_revision_id=working.revision_id,
                opening_id=str(command["opening_id"]),
                station_mm=int(command["station_mm"]),
            )
        elif command_type == "move_wall":
            result = apply_move_wall(
                working,
                base_revision_id=working.revision_id,
                wall_run_id=str(command["wall_run_id"]),
                offset_mm=int(command["offset_mm"]),
            )
        else:
            return RevisionResult(
                False,
                base,
                (f"Operation {operation_index}: unsupported command {command_type}",),
            )
        if not result.accepted:
            return RevisionResult(
                False,
                base,
                tuple(
                    f"Operation {operation_index}: {error}"
                    for error in result.errors
                ),
            )
        working = result.revision
    transaction_command = json.dumps(
        {
            "type": "transaction",
            "commands": commands,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    draft = PlanRevision(
        revision_id="",
        parent_id=base.revision_id,
        vertices=working.vertices,
        half_edges=working.half_edges,
        faces=working.faces,
        wall_runs=working.wall_runs,
        openings=working.openings,
        minimum_safe_span_mm=base.minimum_safe_span_mm,
        minimum_opening_edge_clearance_mm=base.minimum_opening_edge_clearance_mm,
        operations=base.operations + (transaction_command,),
    )
    committed = replace(draft, revision_id=revision_hash(draft))
    committed_errors = validate_dcel(committed)
    if committed_errors:
        return RevisionResult(False, base, tuple(committed_errors))
    return RevisionResult(True, committed)


def validate_dcel(revision: PlanRevision) -> list[str]:
    errors: list[str] = []
    for label, items in (
        ("vertex", revision.vertices),
        ("half-edge", revision.half_edges),
        ("face", revision.faces),
        ("wall-run", revision.wall_runs),
        ("opening", revision.openings),
    ):
        for duplicate in sorted(_duplicate_ids(items)):
            errors.append(f"Duplicate {label} ID {duplicate}")

    vertex_map = {item.id: item for item in revision.vertices}
    edge_map = {item.id: item for item in revision.half_edges}
    face_map = {item.id: item for item in revision.faces}
    run_map = {item.id: item for item in revision.wall_runs}

    for vertex in revision.vertices:
        if not all(math.isfinite(value) for value in (vertex.x_mm, vertex.y_mm)):
            errors.append(f"Vertex {vertex.id} has non-finite coordinates")

    for edge in revision.half_edges:
        if edge.origin_vertex_id not in vertex_map:
            errors.append(f"Half-edge {edge.id} has missing origin {edge.origin_vertex_id}")
        twin = edge_map.get(edge.twin_id)
        if twin is None:
            errors.append(f"Half-edge {edge.id} has missing twin {edge.twin_id}")
        else:
            if twin.twin_id != edge.id:
                errors.append(f"Half-edge {edge.id} twin relationship is not reciprocal")
            if twin.wall_run_id != edge.wall_run_id:
                errors.append(f"Half-edge {edge.id} and its twin use different wall runs")
        next_edge = edge_map.get(edge.next_id)
        prev_edge = edge_map.get(edge.prev_id)
        if next_edge is None:
            errors.append(f"Half-edge {edge.id} has missing next {edge.next_id}")
        elif next_edge.prev_id != edge.id:
            errors.append(f"Half-edge {edge.id} next/prev relationship is not reciprocal")
        elif twin is not None and twin.origin_vertex_id != next_edge.origin_vertex_id:
            errors.append(
                f"Half-edge {edge.id} breaks geometric continuity with {next_edge.id}"
            )
        if prev_edge is None:
            errors.append(f"Half-edge {edge.id} has missing prev {edge.prev_id}")
        elif prev_edge.next_id != edge.id:
            errors.append(f"Half-edge {edge.id} prev/next relationship is not reciprocal")
        if edge.face_id not in face_map:
            errors.append(f"Half-edge {edge.id} has missing face {edge.face_id}")
        if edge.wall_run_id not in run_map:
            errors.append(f"Half-edge {edge.id} has missing wall run {edge.wall_run_id}")

    for face in revision.faces:
        _, cycle_error = _face_cycle(face, edge_map)
        if cycle_error:
            errors.append(cycle_error)

    for wall_run in revision.wall_runs:
        if wall_run.start_vertex_id not in vertex_map or wall_run.end_vertex_id not in vertex_map:
            errors.append(f"Wall run {wall_run.id} references a missing endpoint")
            continue
        start = vertex_map[wall_run.start_vertex_id]
        end = vertex_map[wall_run.end_vertex_id]
        if start.id == end.id or (start.x_mm, start.y_mm) == (end.x_mm, end.y_mm):
            errors.append(f"Wall run {wall_run.id} has zero length")
        run_edges = [edge for edge in revision.half_edges if edge.wall_run_id == wall_run.id]
        if len(run_edges) < 2 or len(run_edges) % 2:
            errors.append(
                f"Wall run {wall_run.id} must contain complete half-edge twin pairs"
            )
            continue
        pair_keys: set[frozenset[str]] = set()
        support_x = end.x_mm - start.x_mm
        support_y = end.y_mm - start.y_mm
        support_length_squared = support_x * support_x + support_y * support_y
        segment_lines: list[LineString] = []
        for edge in run_edges:
            twin = edge_map.get(edge.twin_id)
            if twin is None or twin.wall_run_id != wall_run.id:
                continue
            pair_key = frozenset((edge.id, twin.id))
            if pair_key in pair_keys:
                continue
            pair_keys.add(pair_key)
            if edge.origin_vertex_id not in vertex_map or twin.origin_vertex_id not in vertex_map:
                continue
            segment_start = vertex_map[edge.origin_vertex_id]
            segment_end = vertex_map[twin.origin_vertex_id]
            segment_lines.append(
                LineString(
                    [
                        (segment_start.x_mm, segment_start.y_mm),
                        (segment_end.x_mm, segment_end.y_mm),
                    ]
                )
            )
            for point in (segment_start, segment_end):
                point_x = point.x_mm - start.x_mm
                point_y = point.y_mm - start.y_mm
                cross_product = support_x * point_y - support_y * point_x
                station_numerator = support_x * point_x + support_y * point_y
                if cross_product != 0 or not (
                    0 <= station_numerator <= support_length_squared
                ):
                    errors.append(
                        f"Wall run {wall_run.id} contains a segment outside its support"
                    )
                    break
        if len(pair_keys) * 2 != len(run_edges):
            errors.append(f"Wall run {wall_run.id} has incomplete twin pairing")
        if segment_lines:
            support_line = LineString(
                [(start.x_mm, start.y_mm), (end.x_mm, end.y_mm)]
            )
            covered_line = unary_union(segment_lines)
            if covered_line.symmetric_difference(support_line).length > 0.001:
                errors.append(
                    f"Wall run {wall_run.id} segments do not cover its support exactly"
                )

    exterior_faces = [face for face in revision.faces if face.kind == "exterior"]
    if len(exterior_faces) != 1:
        errors.append("DCEL must contain exactly one exterior face")

    for opening in revision.openings:
        wall_run = run_map.get(opening.wall_run_id)
        if wall_run is None:
            errors.append(f"Opening {opening.id} references missing wall run")
            continue
        if opening.width_mm <= 0:
            errors.append(f"Opening {opening.id} must have positive width")
        start = vertex_map[wall_run.start_vertex_id]
        end = vertex_map[wall_run.end_vertex_id]
        length = round(math.hypot(end.x_mm - start.x_mm, end.y_mm - start.y_mm))
        opening_start = opening.station_mm - opening.width_mm / 2
        opening_end = opening.station_mm + opening.width_mm / 2
        if opening_start < 0 or opening_end > length:
            errors.append(f"Opening {opening.id} lies outside its wall run")
        elif (
            opening_start < revision.minimum_opening_edge_clearance_mm
            or length - opening_end < revision.minimum_opening_edge_clearance_mm
        ):
            errors.append(
                f"Opening {opening.id} violates the minimum edge clearance "
                f"{revision.minimum_opening_edge_clearance_mm}mm"
            )

    openings_by_run: dict[str, list[Opening]] = {}
    for opening in revision.openings:
        openings_by_run.setdefault(opening.wall_run_id, []).append(opening)
    for wall_run_id, wall_openings in openings_by_run.items():
        ordered = sorted(
            wall_openings,
            key=lambda item: item.station_mm - item.width_mm / 2,
        )
        for previous, current in zip(ordered, ordered[1:]):
            previous_end = previous.station_mm + previous.width_mm / 2
            current_start = current.station_mm - current.width_mm / 2
            if current_start < previous_end:
                errors.append(
                    f"Openings {previous.id} and {current.id} overlap on wall run "
                    f"{wall_run_id}"
                )

    if not errors:
        errors.extend(_validate_geometry_differential(revision))

    if not errors:
        errors.extend(_validate_reachability(revision))

    if revision.revision_id != revision_hash(replace(revision, revision_id="")):
        errors.append("Revision content hash does not match revision_id")
    return errors
