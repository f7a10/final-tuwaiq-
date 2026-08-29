from dataclasses import replace

import pytest

from dcel_editor import (
    Opening,
    apply_add_opening,
    apply_merge_faces,
    apply_move_opening,
    apply_move_wall,
    apply_node_wall_run,
    apply_remove_opening,
    apply_split_face,
    apply_split_face_by_wall_stations,
    apply_transaction,
    face_area_m2,
    make_two_room_revision,
    opening_segment_mm,
    validate_dcel,
)


def test_two_room_revision_satisfies_all_half_edge_invariants():
    revision = make_two_room_revision()

    assert validate_dcel(revision) == []
    assert {face.id for face in revision.faces if face.kind == "room"} == {
        "left",
        "right",
    }
    assert len(revision.half_edges) == 14
    assert revision.parent_id is None
    assert revision.revision_id


def test_missing_twin_is_reported_without_mutating_revision():
    revision = make_two_room_revision()
    broken_edge = next(edge for edge in revision.half_edges if edge.id == "shared-left")
    broken = replace(broken_edge, twin_id="missing-edge")
    malformed = replace(
        revision,
        half_edges=tuple(
            broken if edge.id == broken.id else edge for edge in revision.half_edges
        ),
    )

    errors = validate_dcel(malformed)

    assert any("missing twin" in error.lower() for error in errors)
    assert validate_dcel(revision) == []


def test_disconnected_face_cycle_reports_geometric_continuity_error():
    revision = make_two_room_revision()
    malformed = replace(
        revision,
        half_edges=tuple(
            replace(edge, origin_vertex_id="v83")
            if edge.id == "tl-left"
            else edge
            for edge in revision.half_edges
        ),
    )

    errors = validate_dcel(malformed)

    assert any("geometric continuity" in error.lower() for error in errors)
    assert validate_dcel(revision) == []


def test_move_shared_wall_creates_deterministic_immutable_revision():
    base = make_two_room_revision()

    result = apply_move_wall(
        base,
        base_revision_id=base.revision_id,
        wall_run_id="shared",
        offset_mm=500,
    )

    assert result.accepted is True
    assert not result.errors
    child = result.revision
    assert child.parent_id == base.revision_id
    assert child.revision_id != base.revision_id
    assert validate_dcel(child) == []
    assert face_area_m2(child, "left") == pytest.approx(13.5)
    assert face_area_m2(child, "right") == pytest.approx(10.5)
    opening_start, opening_end = opening_segment_mm(child, "shared-door")
    assert opening_start[0] == pytest.approx(4500)
    assert opening_end[0] == pytest.approx(4500)

    assert face_area_m2(base, "left") == pytest.approx(12.0)
    assert face_area_m2(base, "right") == pytest.approx(12.0)

    replay = apply_move_wall(
        base,
        base_revision_id=base.revision_id,
        wall_run_id="shared",
        offset_mm=500,
    )
    assert replay.accepted is True
    assert replay.revision.revision_id == child.revision_id


def test_zero_distance_wall_move_does_not_create_revision():
    base = make_two_room_revision()

    result = apply_move_wall(
        base,
        base_revision_id=base.revision_id,
        wall_run_id="shared",
        offset_mm=0,
    )

    assert result.accepted is False
    assert result.revision is base
    assert any("no-op" in error.lower() for error in result.errors)


def test_move_opening_changes_metric_station_in_new_revision():
    base = make_two_room_revision()

    result = apply_move_opening(
        base,
        base_revision_id=base.revision_id,
        opening_id="entrance",
        station_mm=2000,
    )

    assert result.accepted is True
    moved = result.revision
    assert moved.parent_id == base.revision_id
    assert validate_dcel(moved) == []
    moved_start, moved_end = opening_segment_mm(moved, "entrance")
    assert moved_start == pytest.approx((0, 1550))
    assert moved_end == pytest.approx((0, 2450))
    original_start, original_end = opening_segment_mm(base, "entrance")
    assert original_start == pytest.approx((0, 1050))
    assert original_end == pytest.approx((0, 1950))


def test_move_opening_below_edge_clearance_is_rejected_atomically():
    base = make_two_room_revision()

    result = apply_move_opening(
        base,
        base_revision_id=base.revision_id,
        opening_id="entrance",
        station_mm=500,
    )

    assert result.accepted is False
    assert result.revision is base
    assert any("edge clearance" in error.lower() for error in result.errors)
    original_start, original_end = opening_segment_mm(base, "entrance")
    assert original_start == pytest.approx((0, 1050))
    assert original_end == pytest.approx((0, 1950))


def test_add_wall_anchored_opening_creates_new_revision():
    base = make_two_room_revision()

    result = apply_add_opening(
        base,
        base_revision_id=base.revision_id,
        opening=Opening(
            "living-window",
            "bottom-boundary",
            2000,
            1000,
            kind="window",
        ),
    )

    assert result.accepted is True
    added = result.revision
    assert added.parent_id == base.revision_id
    assert validate_dcel(added) == []
    assert any(opening.id == "living-window" for opening in added.openings)
    window_start, window_end = opening_segment_mm(added, "living-window")
    assert window_start == pytest.approx((1500, 0))
    assert window_end == pytest.approx((2500, 0))
    assert all(opening.id != "living-window" for opening in base.openings)


def test_add_overlapping_opening_is_rejected_atomically():
    base = make_two_room_revision()
    first_result = apply_add_opening(
        base,
        base_revision_id=base.revision_id,
        opening=Opening(
            "first-window",
            "bottom-boundary",
            2000,
            1000,
            kind="window",
        ),
    )
    assert first_result.accepted is True
    with_window = first_result.revision

    result = apply_add_opening(
        with_window,
        base_revision_id=with_window.revision_id,
        opening=Opening(
            "overlapping-window",
            "bottom-boundary",
            2400,
            600,
            kind="window",
        ),
    )

    assert result.accepted is False
    assert result.revision is with_window
    assert any("overlap" in error.lower() for error in result.errors)
    assert all(
        opening.id != "overlapping-window" for opening in with_window.openings
    )
    assert validate_dcel(with_window) == []


def test_remove_only_connecting_door_is_rejected_atomically():
    base = make_two_room_revision()

    result = apply_remove_opening(
        base,
        base_revision_id=base.revision_id,
        opening_id="shared-door",
    )

    assert result.accepted is False
    assert result.revision is base
    assert any("unreachable" in error.lower() for error in result.errors)
    assert any(opening.id == "shared-door" for opening in base.openings)
    assert validate_dcel(base) == []


def test_failed_multi_command_transaction_rolls_back_every_operation():
    base = make_two_room_revision()
    original_entrance = opening_segment_mm(base, "entrance")

    result = apply_transaction(
        base,
        base_revision_id=base.revision_id,
        commands=(
            {
                "type": "move_opening",
                "opening_id": "entrance",
                "station_mm": 2000,
            },
            {
                "type": "move_wall",
                "wall_run_id": "shared",
                "offset_mm": 3500,
            },
        ),
    )

    assert result.accepted is False
    assert result.revision is base
    assert any("operation 2" in error.lower() for error in result.errors)
    current_entrance = opening_segment_mm(base, "entrance")
    assert current_entrance[0] == pytest.approx(original_entrance[0])
    assert current_entrance[1] == pytest.approx(original_entrance[1])
    assert face_area_m2(base, "left") == pytest.approx(12.0)
    assert face_area_m2(base, "right") == pytest.approx(12.0)


def test_successful_multi_command_transaction_commits_one_revision():
    base = make_two_room_revision()
    commands = (
        {
            "type": "move_opening",
            "opening_id": "entrance",
            "station_mm": 2000,
        },
        {
            "type": "move_wall",
            "wall_run_id": "shared",
            "offset_mm": 500,
        },
    )

    result = apply_transaction(
        base,
        base_revision_id=base.revision_id,
        commands=commands,
    )

    assert result.accepted is True
    committed = result.revision
    assert committed.parent_id == base.revision_id
    assert len(committed.operations) == len(base.operations) + 1
    assert validate_dcel(committed) == []
    assert face_area_m2(committed, "left") == pytest.approx(13.5)
    assert face_area_m2(committed, "right") == pytest.approx(10.5)
    entrance_start, entrance_end = opening_segment_mm(committed, "entrance")
    assert entrance_start == pytest.approx((0, 1550))
    assert entrance_end == pytest.approx((0, 2450))

    replay = apply_transaction(
        base,
        base_revision_id=base.revision_id,
        commands=commands,
    )
    assert replay.accepted is True
    assert replay.revision.revision_id == committed.revision_id
    assert face_area_m2(base, "left") == pytest.approx(12.0)
    assert opening_segment_mm(base, "entrance")[0] == pytest.approx((0, 1050))


def test_move_wall_that_breaks_face_partition_is_rejected_atomically():
    base = make_two_room_revision()

    result = apply_move_wall(
        base,
        base_revision_id=base.revision_id,
        wall_run_id="shared",
        offset_mm=4500,
    )

    assert result.accepted is False
    assert result.revision is base
    assert any(
        "geometry" in error.lower()
        or "footprint" in error.lower()
        or "partition" in error.lower()
        or "support" in error.lower()
        for error in result.errors
    )
    assert validate_dcel(base) == []


def test_move_wall_below_minimum_room_span_is_rejected():
    base = make_two_room_revision()

    result = apply_move_wall(
        base,
        base_revision_id=base.revision_id,
        wall_run_id="shared",
        offset_mm=3500,
    )

    assert result.accepted is False
    assert result.revision is base
    assert any("minimum span" in error.lower() for error in result.errors)
    assert face_area_m2(base, "right") == pytest.approx(12.0)


def test_merge_rejects_partition_opening_without_explicit_disposition():
    base = make_two_room_revision()

    result = apply_merge_faces(
        base,
        base_revision_id=base.revision_id,
        partition_wall_run_id="shared",
        survivor_face_id="left",
    )

    assert result.accepted is False
    assert result.revision is base
    assert any("opening disposition" in error.lower() for error in result.errors)
    assert validate_dcel(base) == []


def test_merge_removes_partition_and_opening_into_new_revision():
    base = make_two_room_revision()

    result = apply_merge_faces(
        base,
        base_revision_id=base.revision_id,
        partition_wall_run_id="shared",
        survivor_face_id="left",
        opening_disposition="remove",
    )

    assert result.accepted is True
    merged = result.revision
    assert merged.parent_id == base.revision_id
    assert validate_dcel(merged) == []
    assert {face.id for face in merged.faces if face.kind == "room"} == {"left"}
    assert face_area_m2(merged, "left") == pytest.approx(24.0)
    assert all(run.id != "shared" for run in merged.wall_runs)
    assert all(edge.wall_run_id != "shared" for edge in merged.half_edges)
    assert all(opening.id != "shared-door" for opening in merged.openings)

    assert {face.id for face in base.faces if face.kind == "room"} == {
        "left",
        "right",
    }
    assert any(run.id == "shared" for run in base.wall_runs)


def test_split_noded_face_restores_partition_and_wall_anchored_opening():
    original = make_two_room_revision()
    merge_result = apply_merge_faces(
        original,
        base_revision_id=original.revision_id,
        partition_wall_run_id="shared",
        survivor_face_id="left",
        opening_disposition="remove",
    )
    assert merge_result.accepted is True
    merged = merge_result.revision

    result = apply_split_face(
        merged,
        base_revision_id=merged.revision_id,
        face_id="left",
        start_vertex_id="v40",
        end_vertex_id="v43",
        new_face_id="right",
        wall_run_id="shared",
        opening=Opening("shared-door", "shared", 1500, 900),
    )

    assert result.accepted is True
    split = result.revision
    assert split.parent_id == merged.revision_id
    assert validate_dcel(split) == []
    assert face_area_m2(split, "left") == pytest.approx(12.0)
    assert face_area_m2(split, "right") == pytest.approx(12.0)
    assert any(run.id == "shared" for run in split.wall_runs)
    assert any(opening.id == "shared-door" for opening in split.openings)
    opening_start, opening_end = opening_segment_mm(split, "shared-door")
    assert opening_start[0] == pytest.approx(4000)
    assert opening_end[0] == pytest.approx(4000)

    assert {face.id for face in merged.faces if face.kind == "room"} == {"left"}
    assert all(run.id != "shared" for run in merged.wall_runs)


def test_wall_run_identity_spans_noded_segments_and_survives_move():
    base = make_two_room_revision()

    bottom = next(run for run in base.wall_runs if run.id == "bottom-boundary")
    assert (bottom.start_vertex_id, bottom.end_vertex_id) == ("v00", "v80")
    assert sum(
        edge.wall_run_id == "bottom-boundary" for edge in base.half_edges
    ) == 4

    result = apply_move_wall(
        base,
        base_revision_id=base.revision_id,
        wall_run_id="shared",
        offset_mm=500,
    )

    assert result.accepted is True
    moved_bottom = next(
        run for run in result.revision.wall_runs if run.id == "bottom-boundary"
    )
    assert moved_bottom == bottom
    assert sum(
        edge.wall_run_id == "bottom-boundary"
        for edge in result.revision.half_edges
    ) == 4


def test_noding_wall_run_preserves_identity_and_opening_world_position():
    base = make_two_room_revision()
    original_run = next(run for run in base.wall_runs if run.id == "left-boundary")
    original_opening = opening_segment_mm(base, "entrance")

    result = apply_node_wall_run(
        base,
        base_revision_id=base.revision_id,
        wall_run_id="left-boundary",
        station_mm=1000,
        vertex_id="v01",
    )

    assert result.accepted is True
    noded = result.revision
    assert noded.parent_id == base.revision_id
    assert validate_dcel(noded) == []
    assert next(run for run in noded.wall_runs if run.id == "left-boundary") == original_run
    assert sum(
        edge.wall_run_id == "left-boundary" for edge in noded.half_edges
    ) == 4
    noded_opening = opening_segment_mm(noded, "entrance")
    assert noded_opening[0] == pytest.approx(original_opening[0])
    assert noded_opening[1] == pytest.approx(original_opening[1])

    assert all(vertex.id != "v01" for vertex in base.vertices)
    assert sum(
        edge.wall_run_id == "left-boundary" for edge in base.half_edges
    ) == 2


def test_split_by_wall_stations_is_one_atomic_revision():
    original = make_two_room_revision()
    merge_result = apply_merge_faces(
        original,
        base_revision_id=original.revision_id,
        partition_wall_run_id="shared",
        survivor_face_id="left",
        opening_disposition="remove",
    )
    assert merge_result.accepted is True
    merged = merge_result.revision
    original_entrance = opening_segment_mm(merged, "entrance")

    result = apply_split_face_by_wall_stations(
        merged,
        base_revision_id=merged.revision_id,
        face_id="left",
        first_wall_run_id="left-boundary",
        first_station_mm=2200,
        first_vertex_id="v022",
        second_wall_run_id="right-boundary",
        second_station_mm=2200,
        second_vertex_id="v822",
        new_face_id="lower",
        partition_wall_run_id="horizontal-partition",
        opening=Opening(
            "partition-door",
            "horizontal-partition",
            4000,
            900,
        ),
    )

    assert result.accepted is True
    split = result.revision
    assert split.parent_id == merged.revision_id
    assert len(split.operations) == len(merged.operations) + 1
    assert validate_dcel(split) == []
    assert face_area_m2(split, "left") == pytest.approx(6.4)
    assert face_area_m2(split, "lower") == pytest.approx(17.6)
    assert {vertex.id for vertex in split.vertices}.issuperset({"v022", "v822"})
    assert any(run.id == "horizontal-partition" for run in split.wall_runs)
    assert any(opening.id == "partition-door" for opening in split.openings)
    moved_entrance = opening_segment_mm(split, "entrance")
    assert moved_entrance[0] == pytest.approx(original_entrance[0])
    assert moved_entrance[1] == pytest.approx(original_entrance[1])

    assert all(vertex.id not in {"v022", "v822"} for vertex in merged.vertices)
    assert {face.id for face in merged.faces if face.kind == "room"} == {"left"}


def test_split_without_door_is_rejected_as_unreachable_atomically():
    original = make_two_room_revision()
    merge_result = apply_merge_faces(
        original,
        base_revision_id=original.revision_id,
        partition_wall_run_id="shared",
        survivor_face_id="left",
        opening_disposition="remove",
    )
    assert merge_result.accepted is True
    merged = merge_result.revision

    result = apply_split_face_by_wall_stations(
        merged,
        base_revision_id=merged.revision_id,
        face_id="left",
        first_wall_run_id="left-boundary",
        first_station_mm=2200,
        first_vertex_id="v022-no-door",
        second_wall_run_id="right-boundary",
        second_station_mm=2200,
        second_vertex_id="v822-no-door",
        new_face_id="lower-no-door",
        partition_wall_run_id="closed-partition",
    )

    assert result.accepted is False
    assert result.revision is merged
    assert any("unreachable" in error.lower() for error in result.errors)
    assert all(
        vertex.id not in {"v022-no-door", "v822-no-door"}
        for vertex in merged.vertices
    )
    assert validate_dcel(merged) == []
