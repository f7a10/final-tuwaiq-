import pytest

from editor_topology import (
    apply_topology_transaction,
    make_single_room_plan,
    opening_segment,
    room_area,
    wall_ids_for_lineage,
)


def test_split_room_nodes_boundary_walls_and_preserves_opening_position():
    source = make_single_room_plan()
    original_opening = opening_segment(source, "entrance")

    result = apply_topology_transaction(
        source,
        [
            {
                "type": "split_room",
                "room_id": "main",
                "wall_id": "partition-horizontal",
                "start": [0.0, 3.0],
                "end": [8.0, 3.0],
                "child_room_ids": ["lower", "upper"],
            }
        ],
    )

    assert result.accepted is True
    assert result.errors == []
    assert set(result.plan.rooms) == {"lower", "upper"}
    assert room_area(result.plan, "lower") == pytest.approx(24.0)
    assert room_area(result.plan, "upper") == pytest.approx(24.0)
    remapped_opening = opening_segment(result.plan, "entrance")
    assert remapped_opening[0] == pytest.approx(original_opening[0])
    assert remapped_opening[1] == pytest.approx(original_opening[1])
    assert len(wall_ids_for_lineage(result.plan, "left-boundary")) == 2
    assert len(wall_ids_for_lineage(result.plan, "right-boundary")) == 2

    assert set(source.rooms) == {"main"}
    assert len(wall_ids_for_lineage(source, "left-boundary")) == 1


def test_merge_rooms_removes_partition_and_compacts_wall_lineages():
    source = make_single_room_plan()
    split_result = apply_topology_transaction(
        source,
        [
            {
                "type": "split_room",
                "room_id": "main",
                "wall_id": "partition-horizontal",
                "start": [0.0, 3.0],
                "end": [8.0, 3.0],
                "child_room_ids": ["lower", "upper"],
            }
        ],
    )
    assert split_result.accepted is True

    merge_result = apply_topology_transaction(
        split_result.plan,
        [
            {
                "type": "merge_rooms",
                "room_ids": ["lower", "upper"],
                "wall_lineage_id": "partition-horizontal",
                "merged_room_id": "main-again",
            }
        ],
    )

    assert merge_result.accepted is True
    assert set(merge_result.plan.rooms) == {"main-again"}
    assert room_area(merge_result.plan, "main-again") == pytest.approx(48.0)
    assert wall_ids_for_lineage(merge_result.plan, "partition-horizontal") == []
    assert len(wall_ids_for_lineage(merge_result.plan, "left-boundary")) == 1
    assert len(wall_ids_for_lineage(merge_result.plan, "right-boundary")) == 1

    assert set(split_result.plan.rooms) == {"lower", "upper"}


def test_move_partition_rebuilds_faces_and_preserves_room_identity():
    source = make_single_room_plan()
    split_result = apply_topology_transaction(
        source,
        [
            {
                "type": "split_room",
                "room_id": "main",
                "wall_id": "partition-horizontal",
                "start": [0.0, 3.0],
                "end": [8.0, 3.0],
                "child_room_ids": ["lower", "upper"],
            }
        ],
    )
    original_opening = opening_segment(split_result.plan, "entrance")

    move_result = apply_topology_transaction(
        split_result.plan,
        [
            {
                "type": "move_wall",
                "wall_lineage_id": "partition-horizontal",
                "offset": 1.0,
            }
        ],
    )

    assert move_result.accepted is True
    assert room_area(move_result.plan, "lower") == pytest.approx(32.0)
    assert room_area(move_result.plan, "upper") == pytest.approx(16.0)
    remapped_opening = opening_segment(move_result.plan, "entrance")
    assert remapped_opening[0] == pytest.approx(original_opening[0])
    assert remapped_opening[1] == pytest.approx(original_opening[1])
    assert room_area(split_result.plan, "lower") == pytest.approx(24.0)
    assert room_area(split_result.plan, "upper") == pytest.approx(24.0)


def test_move_partition_that_collapses_room_is_rejected_atomically():
    source = make_single_room_plan()
    split_result = apply_topology_transaction(
        source,
        [
            {
                "type": "split_room",
                "room_id": "main",
                "wall_id": "partition-horizontal",
                "start": [0.0, 3.0],
                "end": [8.0, 3.0],
                "child_room_ids": ["lower", "upper"],
            }
        ],
    )

    move_result = apply_topology_transaction(
        split_result.plan,
        [
            {
                "type": "move_wall",
                "wall_lineage_id": "partition-horizontal",
                "offset": 2.5,
            }
        ],
    )

    assert move_result.accepted is False
    assert any("minimum span" in error.lower() for error in move_result.errors)
    assert move_result.plan is split_result.plan
    assert room_area(split_result.plan, "lower") == pytest.approx(24.0)
    assert room_area(split_result.plan, "upper") == pytest.approx(24.0)


def test_split_wall_with_interior_endpoint_is_rejected():
    source = make_single_room_plan()

    result = apply_topology_transaction(
        source,
        [
            {
                "type": "split_room",
                "room_id": "main",
                "wall_id": "invalid-partition",
                "start": [1.0, 3.0],
                "end": [8.0, 3.0],
                "child_room_ids": ["one", "two"],
            }
        ],
    )

    assert result.accepted is False
    assert any("endpoints" in error.lower() and "boundary" in error.lower() for error in result.errors)
    assert result.plan is source


def test_split_wall_through_opening_is_rejected():
    source = make_single_room_plan()

    result = apply_topology_transaction(
        source,
        [
            {
                "type": "split_room",
                "room_id": "main",
                "wall_id": "door-crossing-partition",
                "start": [0.0, 1.5],
                "end": [8.0, 1.5],
                "child_room_ids": ["lower", "upper"],
            }
        ],
    )

    assert result.accepted is False
    assert any("opening entrance" in error.lower() and "wall segment" in error.lower() for error in result.errors)
    assert result.plan is source


def test_open_wall_network_is_rejected_even_if_stored_room_polygon_is_closed():
    malformed = make_single_room_plan()
    del malformed.walls["top-boundary"]

    result = apply_topology_transaction(malformed, [])

    assert result.accepted is False
    assert any("wall network" in error.lower() and "footprint" in error.lower() for error in result.errors)
    assert result.plan is malformed
