import random

import pytest

from editor_geometry import (
    Opening,
    apply_transaction,
    make_two_room_plan,
    opening_segment,
    room_area,
)


def test_move_shared_wall_updates_both_rooms_and_keeps_door_anchored():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [{"type": "move_wall", "wall_id": "shared", "offset": 0.5}],
    )

    assert result.accepted is True
    assert result.errors == []
    assert room_area(result.plan, "left") == pytest.approx(13.5)
    assert room_area(result.plan, "right") == pytest.approx(10.5)

    door_start, door_end = opening_segment(result.plan, "shared-door")
    assert door_start[0] == pytest.approx(4.5)
    assert door_end[0] == pytest.approx(4.5)

    # Preview transactions must never mutate the authoritative source plan.
    assert room_area(original, "left") == pytest.approx(12.0)
    assert room_area(original, "right") == pytest.approx(12.0)


def test_locked_exterior_wall_move_is_rejected_without_mutating_source():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [{"type": "move_wall", "wall_id": "left", "offset": 0.5}],
    )

    assert result.accepted is False
    assert any("locked" in error.lower() for error in result.errors)
    assert result.plan is original
    assert original.vertices["v00"].x == pytest.approx(0.0)
    assert original.vertices["v01"].x == pytest.approx(0.0)


def test_wall_move_that_collapses_room_below_safe_span_is_rejected():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [{"type": "move_wall", "wall_id": "shared", "offset": 3.4}],
    )

    assert result.accepted is False
    assert any("minimum span" in error.lower() for error in result.errors)
    assert result.plan is original
    assert room_area(original, "right") == pytest.approx(12.0)


def test_multi_operation_transaction_rolls_back_and_identifies_failed_step():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [
            {"type": "move_wall", "wall_id": "shared", "offset": 0.5},
            {"type": "move_wall", "wall_id": "left", "offset": 0.2},
        ],
    )

    assert result.accepted is False
    assert result.plan is original
    assert result.errors[0].startswith("Operation 2:")
    assert "locked" in result.errors[0].lower()
    assert room_area(original, "left") == pytest.approx(12.0)
    assert room_area(original, "right") == pytest.approx(12.0)


def test_wall_move_outside_building_footprint_is_rejected():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [{"type": "move_wall", "wall_id": "shared", "offset": 5.0}],
    )

    assert result.accepted is False
    assert any("footprint" in error.lower() for error in result.errors)
    assert result.plan is original


def test_move_opening_uses_physical_wall_offset_and_keeps_it_attached():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [
            {
                "type": "move_opening",
                "opening_id": "shared-door",
                "center_offset": 0.8,
            }
        ],
    )

    assert result.accepted is True
    door_start, door_end = opening_segment(result.plan, "shared-door")
    assert door_start[0] == pytest.approx(4.0)
    assert door_end[0] == pytest.approx(4.0)
    assert (door_start[1] + door_end[1]) / 2 == pytest.approx(0.8)

    original_start, original_end = opening_segment(original, "shared-door")
    assert (original_start[1] + original_end[1]) / 2 == pytest.approx(1.5)


def test_opening_move_without_end_clearance_is_rejected():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [
            {
                "type": "move_opening",
                "opening_id": "shared-door",
                "center_offset": 0.3,
            }
        ],
    )

    assert result.accepted is False
    assert any("edge clearance" in error.lower() for error in result.errors)
    assert result.plan is original


def test_self_intersecting_room_blocks_editor_transaction():
    malformed = make_two_room_plan()
    malformed.rooms["left"].vertex_ids = ["v00", "v11", "v10", "v01"]

    result = apply_transaction(malformed, [])

    assert result.accepted is False
    assert any("invalid polygon" in error.lower() for error in result.errors)
    assert result.plan is malformed


def test_overlapping_room_faces_block_editor_transaction():
    malformed = make_two_room_plan()
    malformed.rooms["right"].vertex_ids = list(
        malformed.rooms["left"].vertex_ids
    )

    result = apply_transaction(malformed, [])

    assert result.accepted is False
    assert any("overlap" in error.lower() for error in result.errors)
    assert result.plan is malformed


def test_overlapping_openings_on_same_wall_block_transaction():
    malformed = make_two_room_plan()
    malformed.openings["second-door"] = Opening(
        "second-door",
        wall_id="shared",
        center_ratio=0.6,
        width=0.9,
    )

    result = apply_transaction(malformed, [])

    assert result.accepted is False
    assert any("openings" in error.lower() and "overlap" in error.lower() for error in result.errors)
    assert result.plan is malformed


def test_room_boundary_edge_without_wall_blocks_editor_transaction():
    malformed = make_two_room_plan()
    del malformed.walls["top-left"]

    result = apply_transaction(malformed, [])

    assert result.accepted is False
    assert any("boundary edge" in error.lower() and "wall" in error.lower() for error in result.errors)
    assert result.plan is malformed


def test_opening_with_missing_host_wall_blocks_editor_transaction():
    malformed = make_two_room_plan()
    malformed.openings["shared-door"].wall_id = "missing-wall"

    result = apply_transaction(malformed, [])

    assert result.accepted is False
    assert any("missing host wall" in error.lower() for error in result.errors)
    assert result.plan is malformed


def test_add_opening_creates_wall_anchored_geometry_without_mutating_source():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [
            {
                "type": "add_opening",
                "opening_id": "second-door",
                "wall_id": "shared",
                "center_offset": 2.4,
                "width": 0.6,
                "kind": "door",
            }
        ],
    )

    assert result.accepted is True
    assert "second-door" in result.plan.openings
    start, end = opening_segment(result.plan, "second-door")
    assert start[0] == pytest.approx(4.0)
    assert end[0] == pytest.approx(4.0)
    assert (start[1] + end[1]) / 2 == pytest.approx(2.4)
    assert "second-door" not in original.openings


def test_remove_only_connecting_door_is_rejected_as_unreachable():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [{"type": "remove_opening", "opening_id": "shared-door"}],
    )

    assert result.accepted is False
    assert any("unreachable" in error.lower() and "right" in error.lower() for error in result.errors)
    assert result.plan is original
    assert "shared-door" in original.openings


def test_resize_opening_changes_physical_width_in_preview_only():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [
            {
                "type": "resize_opening",
                "opening_id": "shared-door",
                "width": 1.2,
            }
        ],
    )

    assert result.accepted is True
    start, end = opening_segment(result.plan, "shared-door")
    assert abs(end[1] - start[1]) == pytest.approx(1.2)
    assert original.openings["shared-door"].width == pytest.approx(0.9)


def test_non_positive_opening_width_is_rejected():
    original = make_two_room_plan()

    result = apply_transaction(
        original,
        [
            {
                "type": "resize_opening",
                "opening_id": "shared-door",
                "width": 0.0,
            }
        ],
    )

    assert result.accepted is False
    assert any("positive width" in error.lower() for error in result.errors)
    assert result.plan is original


def test_metric_edit_is_blocked_when_scale_confidence_is_low():
    original = make_two_room_plan()
    original.scale_confidence = 0.45

    result = apply_transaction(
        original,
        [{"type": "move_wall", "wall_id": "shared", "offset": 0.5}],
    )

    assert result.accepted is False
    assert any("scale confidence" in error.lower() for error in result.errors)
    assert result.plan is original
    assert room_area(original, "left") == pytest.approx(12.0)


def test_edit_is_blocked_when_geometry_confidence_is_low():
    original = make_two_room_plan()
    original.geometry_confidence = 0.5

    result = apply_transaction(
        original,
        [{"type": "move_wall", "wall_id": "shared", "offset": 0.5}],
    )

    assert result.accepted is False
    assert any("geometry confidence" in error.lower() for error in result.errors)
    assert result.plan is original


def test_random_wall_move_previews_preserve_partition_and_source():
    source = make_two_room_plan()
    random_generator = random.Random(20260827)
    random_offsets = [random_generator.uniform(-6.0, 6.0) for _ in range(500)]

    for offset in random_offsets:
        result = apply_transaction(
            source,
            [{"type": "move_wall", "wall_id": "shared", "offset": offset}],
        )

        assert room_area(source, "left") == pytest.approx(12.0)
        assert room_area(source, "right") == pytest.approx(12.0)
        if result.accepted:
            assert room_area(result.plan, "left") + room_area(
                result.plan, "right"
            ) == pytest.approx(24.0)
            assert room_area(result.plan, "left") >= 2.4 - 1e-9
            assert room_area(result.plan, "right") >= 2.4 - 1e-9
        else:
            assert result.errors
