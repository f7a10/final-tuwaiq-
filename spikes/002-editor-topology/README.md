# Spike 002: Wall-Line Topology and Derived Room Faces

## Question

Can Emad keep wall lineages and openings stable while rebuilding room faces from a noded wall network after split, merge, and move operations?

## Approach tested

- Wall segments are authoritative and carry stable lineage identifiers plus lineage intervals.
- Intersections split walls into child segments while preserving their lineage.
- Rooms are derived by polygonizing the complete noded wall network.
- Stored room faces must match the wall-derived faces.
- Openings retain physical offsets on a wall lineage and remap to the correct child segment.
- Split, merge, and move operations run as immutable transactions.
- Child room IDs are explicit for split operations; moved faces retain IDs by maximum geometric overlap.
- Contiguous child segments compact back into one lineage segment after a merge.

## Implemented operations

- `split_room`
- `merge_rooms`
- `move_wall` for orthogonal walls

## Verified behavior

- Splitting a room creates exactly two faces whose areas preserve the source area.
- Boundary wall segments are automatically noded at new junctions.
- A wall-hosted entrance keeps its physical world position after noding.
- Merging adjacent rooms removes the shared wall, restores one face, and compacts boundary lineages.
- Moving a partition rebuilds faces and preserves semantic room IDs.
- A move that creates a room below the geometry safety span is rejected atomically.
- Split endpoints must lie on the selected room boundary.
- A split that cuts through an opening is rejected because the opening cannot map to one host segment.
- An open wall network is rejected even if a stale stored room polygon appears closed.

## Evidence

Run:

```bash
PYTHONPATH=spikes/002-editor-topology \
  spikes/001-editor-geometry/venv/Scripts/python.exe \
  -m pytest spikes/002-editor-topology/tests -q
```

Latest result:

```text
7 passed in 0.10s
```

## Verdict: PARTIAL

### What worked

A persistent wall-lineage graph plus transaction-time noding and derived polygon faces is viable for Emad V1. It handles the topology changes that the first shared-vertex spike could not express safely.

### Constraints and unresolved work

- Moving angled/curved walls is not implemented; V1 movement is orthogonal only.
- Stable identity matching has only been exercised on simple two-face examples.
- Multi-room junctions, holes/courtyards, wall thickness, columns, shafts, and structural zones need fixtures.
- Merge behavior for doors/windows hosted on a removed partition needs an explicit policy.
- Semantic provenance and confidence must survive split/merge lineage changes.
- Geometry safety checks remain separate from documented SBC rules.

### Recommendation for the real build

Use a persistent wall-lineage planar graph as the canonical editable geometry. Re-node the graph and derive room faces after every preview transaction. Preserve room identity by explicit operation IDs for topology changes and overlap matching for pure movement. Keep openings anchored to lineage intervals, and reject any operation that cannot remap them unambiguously. Do not let the LLM emit final polygons or wall coordinates directly.
