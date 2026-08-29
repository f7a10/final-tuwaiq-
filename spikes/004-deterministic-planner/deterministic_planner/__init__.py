from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from dcel_editor import (
    PlanRevision,
    apply_transaction,
    face_area_m2,
    validate_dcel,
)


@dataclass(frozen=True)
class PlannerRequest:
    wall_run_id: str
    offsets_mm: tuple[int, ...]
    hard_min_area_m2: tuple[tuple[str, float], ...]
    target_area_m2: tuple[tuple[str, float], ...]
    priority_face_id: str
    ruleset_version: str
    engine_version: str
    seed: int
    search_budget: int
    required_opening_stations_mm: tuple[tuple[str, int], ...] = ()
    minimum_diversity_mm: int = 400


@dataclass(frozen=True)
class Candidate:
    profile: str
    candidate_id: str
    offset_mm: int
    plan: PlanRevision
    hard_violation_count: int
    score_components: tuple[tuple[str, float], ...]
    explanation: str
    canonical_json: str


@dataclass(frozen=True)
class PlannerResult:
    status: str
    request_hash: str
    candidates: tuple[Candidate, ...]
    evaluated_count: int
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class _FeasiblePlan:
    offset_mm: int
    plan: PlanRevision
    areas: tuple[tuple[str, float], ...]
    balanced_dissatisfaction: float
    priority_area: float


def _request_payload(request: PlannerRequest) -> dict[str, object]:
    return {
        "wall_run_id": request.wall_run_id,
        "offsets_mm": sorted({int(offset) for offset in request.offsets_mm}),
        "hard_min_area_m2": [
            [face_id, float(area)]
            for face_id, area in sorted(request.hard_min_area_m2)
        ],
        "target_area_m2": [
            [face_id, float(area)]
            for face_id, area in sorted(request.target_area_m2)
        ],
        "priority_face_id": request.priority_face_id,
        "ruleset_version": request.ruleset_version,
        "engine_version": request.engine_version,
        "seed": int(request.seed),
        "search_budget": int(request.search_budget),
        "required_opening_stations_mm": [
            [opening_id, int(station_mm)]
            for opening_id, station_mm in sorted(request.required_opening_stations_mm)
        ],
        "minimum_diversity_mm": int(request.minimum_diversity_mm),
    }


def _canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _hash_payload(payload: dict[str, object]) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _candidate(
    *,
    profile: str,
    feasible: _FeasiblePlan,
    request: PlannerRequest,
    request_hash: str,
) -> Candidate:
    areas = dict(feasible.areas)
    if profile == "minimal":
        scores = (
            ("absolute_wall_move_mm", float(abs(feasible.offset_mm))),
            ("balanced_dissatisfaction_m2", feasible.balanced_dissatisfaction),
        )
    elif profile == "balanced":
        scores = (
            ("balanced_dissatisfaction_m2", feasible.balanced_dissatisfaction),
            ("absolute_wall_move_mm", float(abs(feasible.offset_mm))),
        )
    else:
        scores = (
            ("priority_room_area_m2", feasible.priority_area),
            ("absolute_wall_move_mm", float(abs(feasible.offset_mm))),
        )
    payload: dict[str, object] = {
        "profile": profile,
        "offset_mm": feasible.offset_mm,
        "plan_revision_id": feasible.plan.revision_id,
        "request_hash": request_hash,
        "ruleset_version": request.ruleset_version,
        "engine_version": request.engine_version,
        "seed": request.seed,
        "search_budget": request.search_budget,
        "hard_violation_count": 0,
        "areas_m2": [[face_id, area] for face_id, area in feasible.areas],
        "score_components": [[name, value] for name, value in scores],
    }
    candidate_id = _hash_payload(payload)
    complete_payload = {"candidate_id": candidate_id, **payload}
    explanation = (
        f"{profile}: move {request.wall_run_id} by {feasible.offset_mm}mm; "
        + ", ".join(
            f"{face_id}={areas[face_id]:.2f}m2" for face_id in sorted(areas)
        )
    )
    return Candidate(
        profile=profile,
        candidate_id=candidate_id,
        offset_mm=feasible.offset_mm,
        plan=feasible.plan,
        hard_violation_count=0,
        score_components=scores,
        explanation=explanation,
        canonical_json=_canonical_json(complete_payload),
    )


def generate_repair_candidates(
    base: PlanRevision,
    request: PlannerRequest,
) -> PlannerResult:
    request_payload = _request_payload(request)
    request_hash = _hash_payload(request_payload)
    if request.search_budget <= 0:
        return PlannerResult(
            status="search_budget_exhausted",
            request_hash=request_hash,
            candidates=(),
            evaluated_count=0,
            diagnostics=("search_budget must be positive",),
        )
    if request.wall_run_id not in {run.id for run in base.wall_runs}:
        return PlannerResult(
            status="needs_clarification",
            request_hash=request_hash,
            candidates=(),
            evaluated_count=0,
            diagnostics=(f"Unknown target wall run: {request.wall_run_id}",),
        )

    minimum_areas = dict(request.hard_min_area_m2)
    targets = dict(request.target_area_m2)
    room_face_ids = {
        face.id for face in base.faces if face.kind == "room"
    }
    unknown_faces = sorted((set(minimum_areas) | set(targets) | {request.priority_face_id}) - room_face_ids)
    if unknown_faces:
        return PlannerResult(
            status="needs_clarification",
            request_hash=request_hash,
            candidates=(),
            evaluated_count=0,
            diagnostics=("Unknown room faces: " + ", ".join(unknown_faces),),
        )
    required_minimum_area = sum(minimum_areas.values())
    usable_room_area = sum(face_area_m2(base, face_id) for face_id in room_face_ids)
    if required_minimum_area > usable_room_area:
        constrained_faces = ", ".join(sorted(minimum_areas))
        return PlannerResult(
            status="infeasible_proven",
            request_hash=request_hash,
            candidates=(),
            evaluated_count=0,
            diagnostics=(
                f"Minimum areas for {constrained_faces} require "
                f"{required_minimum_area:.2f}m2 but usable room area is "
                f"{usable_room_area:.2f}m2",
            ),
        )
    relevant_faces = sorted(set(minimum_areas) | set(targets) | {request.priority_face_id})
    feasible_pool: list[_FeasiblePlan] = []
    diagnostics: list[str] = []
    evaluated_count = 0
    current_opening_stations = {
        opening.id: opening.station_mm for opening in base.openings
    }
    unknown_openings = sorted(
        {
            opening_id
            for opening_id, _ in request.required_opening_stations_mm
        }
        - set(current_opening_stations)
    )
    if unknown_openings:
        return PlannerResult(
            status="needs_clarification",
            request_hash=request_hash,
            candidates=(),
            evaluated_count=0,
            diagnostics=(
                "Unknown required openings: " + ", ".join(unknown_openings),
            ),
        )
    for offset_mm in sorted({int(offset) for offset in request.offsets_mm}):
        if evaluated_count >= request.search_budget:
            break
        evaluated_count += 1
        commands: list[dict[str, object]] = [
            {
                "type": "move_opening",
                "opening_id": opening_id,
                "station_mm": int(station_mm),
            }
            for opening_id, station_mm in sorted(
                request.required_opening_stations_mm
            )
            if current_opening_stations.get(opening_id) != int(station_mm)
        ]
        commands.append(
            {
                "type": "move_wall",
                "wall_run_id": request.wall_run_id,
                "offset_mm": offset_mm,
            }
        )
        transaction = apply_transaction(
            base,
            base_revision_id=base.revision_id,
            commands=tuple(commands),
        )
        if not transaction.accepted:
            diagnostics.append(
                f"offset {offset_mm}mm rejected: {'; '.join(transaction.errors)}"
            )
            continue
        plan = transaction.revision
        topology_errors = validate_dcel(plan)
        if topology_errors:
            diagnostics.append(
                f"offset {offset_mm}mm rejected independently: "
                + "; ".join(topology_errors)
            )
            continue
        areas = tuple(
            (face_id, round(face_area_m2(plan, face_id), 6))
            for face_id in relevant_faces
        )
        area_map = dict(areas)
        hard_violations = [
            face_id
            for face_id, minimum_area in minimum_areas.items()
            if area_map[face_id] < minimum_area
        ]
        if hard_violations:
            diagnostics.append(
                f"offset {offset_mm}mm violates minimum area for: "
                + ", ".join(sorted(hard_violations))
            )
            continue
        balanced_dissatisfaction = round(
            sum(abs(area_map[face_id] - target) for face_id, target in targets.items()),
            6,
        )
        feasible_pool.append(
            _FeasiblePlan(
                offset_mm=offset_mm,
                plan=plan,
                areas=areas,
                balanced_dissatisfaction=balanced_dissatisfaction,
                priority_area=area_map[request.priority_face_id],
            )
        )

    if not feasible_pool:
        status = (
            "search_budget_exhausted"
            if evaluated_count < len(set(request.offsets_mm))
            else "infeasible_proven"
        )
        return PlannerResult(
            status=status,
            request_hash=request_hash,
            candidates=(),
            evaluated_count=evaluated_count,
            diagnostics=tuple(diagnostics),
        )

    remaining = list(feasible_pool)
    selected: list[Candidate] = []
    selected_offsets: list[int] = []
    selectors = (
        (
            "minimal",
            lambda item: (
                abs(item.offset_mm),
                item.balanced_dissatisfaction,
                item.plan.revision_id,
            ),
        ),
        (
            "balanced",
            lambda item: (
                item.balanced_dissatisfaction,
                abs(item.offset_mm),
                item.plan.revision_id,
            ),
        ),
        (
            "priority",
            lambda item: (
                -item.priority_area,
                abs(item.offset_mm),
                item.plan.revision_id,
            ),
        ),
    )
    for profile, selector in selectors:
        eligible = [
            item
            for item in remaining
            if all(
                abs(item.offset_mm - selected_offset)
                >= request.minimum_diversity_mm
                for selected_offset in selected_offsets
            )
        ]
        if not eligible:
            diagnostics.append(
                f"No {profile} candidate satisfies minimum diversity "
                f"{request.minimum_diversity_mm}mm"
            )
            continue
        winner = min(eligible, key=selector)
        remaining.remove(winner)
        selected_offsets.append(winner.offset_mm)
        selected.append(
            _candidate(
                profile=profile,
                feasible=winner,
                request=request,
                request_hash=request_hash,
            )
        )

    budget_limited = evaluated_count < len(set(request.offsets_mm))
    if budget_limited:
        diagnostics.append(
            f"Search budget evaluated {evaluated_count} of "
            f"{len(set(request.offsets_mm))} offsets"
        )
    if budget_limited:
        status = "feasible_budget_limited"
    elif len(selected) == 3:
        status = "success"
    else:
        status = "insufficient_diversity"
    return PlannerResult(
        status=status,
        request_hash=request_hash,
        candidates=tuple(selected),
        evaluated_count=evaluated_count,
        diagnostics=tuple(diagnostics),
    )
