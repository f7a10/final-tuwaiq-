from dataclasses import replace

from dcel_editor import (
    face_area_m2,
    make_two_room_revision,
    opening_segment_mm,
    validate_dcel,
)
from deterministic_planner import PlannerRequest, generate_repair_candidates


def make_request() -> PlannerRequest:
    return PlannerRequest(
        wall_run_id="shared",
        offsets_mm=(1500, 500, 1000),
        hard_min_area_m2=(("left", 13.0), ("right", 7.0)),
        target_area_m2=(("left", 15.0), ("right", 9.0)),
        priority_face_id="left",
        ruleset_version="rules-spike-v1",
        engine_version="planner-spike-v1",
        seed=17,
        search_budget=20,
    )


def test_same_request_produces_three_deterministic_valid_profile_candidates():
    base = make_two_room_revision()
    request = make_request()

    first = generate_repair_candidates(base, request)
    second = generate_repair_candidates(base, request)

    assert first.status == "success"
    assert second.status == "success"
    assert first.request_hash == second.request_hash
    assert [candidate.canonical_json for candidate in first.candidates] == [
        candidate.canonical_json for candidate in second.candidates
    ]
    assert [candidate.profile for candidate in first.candidates] == [
        "minimal",
        "balanced",
        "priority",
    ]
    assert [candidate.offset_mm for candidate in first.candidates] == [500, 1000, 1500]
    assert len({candidate.candidate_id for candidate in first.candidates}) == 3
    assert len({candidate.plan.revision_id for candidate in first.candidates}) == 3
    assert all(candidate.hard_violation_count == 0 for candidate in first.candidates)
    assert all(validate_dcel(candidate.plan) == [] for candidate in first.candidates)

    assert face_area_m2(base, "left") == 12.0
    assert face_area_m2(base, "right") == 12.0


def test_impossible_minimum_areas_return_presolve_unsatisfiable_core():
    base = make_two_room_revision()
    request = PlannerRequest(
        wall_run_id="shared",
        offsets_mm=(-1000, 500, 1000),
        hard_min_area_m2=(("left", 20.0), ("right", 20.0)),
        target_area_m2=(("left", 20.0), ("right", 20.0)),
        priority_face_id="left",
        ruleset_version="rules-spike-v1",
        engine_version="planner-spike-v1",
        seed=17,
        search_budget=20,
    )

    result = generate_repair_candidates(base, request)

    assert result.status == "infeasible_proven"
    assert result.candidates == ()
    assert result.evaluated_count == 0
    assert any(
        "40.00m2" in diagnostic
        and "24.00m2" in diagnostic
        and "left" in diagnostic
        and "right" in diagnostic
        for diagnostic in result.diagnostics
    )


def test_feasible_candidate_with_exhausted_budget_is_not_called_low_diversity():
    base = make_two_room_revision()
    request = replace(make_request(), search_budget=1)

    result = generate_repair_candidates(base, request)

    assert result.status == "feasible_budget_limited"
    assert result.evaluated_count == 1
    assert len(result.candidates) == 1
    assert result.candidates[0].profile == "minimal"
    assert result.candidates[0].offset_mm == 500
    assert any("1 of 3" in diagnostic for diagnostic in result.diagnostics)


def test_each_candidate_coordinates_wall_and_opening_repairs_atomically():
    base = make_two_room_revision()
    request = replace(
        make_request(),
        required_opening_stations_mm=(("entrance", 2000),),
    )

    result = generate_repair_candidates(base, request)

    assert result.status == "success"
    assert len(result.candidates) == 3
    for candidate in result.candidates:
        entrance_start, entrance_end = opening_segment_mm(
            candidate.plan,
            "entrance",
        )
        assert entrance_start == (0, 1550)
        assert entrance_end == (0, 2450)
        assert len(candidate.plan.operations) == len(base.operations) + 1
        assert validate_dcel(candidate.plan) == []

    original_start, original_end = opening_segment_mm(base, "entrance")
    assert original_start == (0, 1050)
    assert original_end == (0, 1950)


def test_close_variants_are_not_relabelled_as_three_diverse_candidates():
    base = make_two_room_revision()
    request = replace(
        make_request(),
        offsets_mm=(700, 500, 600),
        minimum_diversity_mm=400,
    )

    result = generate_repair_candidates(base, request)

    assert result.status == "insufficient_diversity"
    assert len(result.candidates) == 1
    assert result.candidates[0].profile == "minimal"
    assert result.candidates[0].offset_mm == 500
    assert any("diversity" in diagnostic.lower() for diagnostic in result.diagnostics)


def test_unknown_required_opening_requests_clarification_before_search():
    base = make_two_room_revision()
    request = replace(
        make_request(),
        required_opening_stations_mm=(("missing-door", 2000),),
    )

    result = generate_repair_candidates(base, request)

    assert result.status == "needs_clarification"
    assert result.evaluated_count == 0
    assert result.candidates == ()
    assert any("missing-door" in diagnostic for diagnostic in result.diagnostics)


def test_unknown_target_wall_requests_clarification_before_search():
    base = make_two_room_revision()
    request = replace(make_request(), wall_run_id="missing-wall")

    result = generate_repair_candidates(base, request)

    assert result.status == "needs_clarification"
    assert result.evaluated_count == 0
    assert result.candidates == ()
    assert any("missing-wall" in diagnostic for diagnostic in result.diagnostics)
