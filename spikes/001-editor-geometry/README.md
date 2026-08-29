# Spike 001: Editor Geometry and Atomic Transactions

## Question

Given a residential floor-plan model with shared walls and wall-anchored openings, when an edit changes geometry, can Emad update every dependent room/opening consistently and reject unsafe edits without mutating the source plan?

## Why this is the highest-risk editor question

The editor is useless if rooms drift apart, doors detach from walls, inaccessible spaces are created, invalid geometry is partially applied, or AI-generated operations silently corrupt the plan. This spike validates the transaction and constraint boundary before any production UI integration.

## Tested model

- Vertices are shared geometric points.
- Walls reference two shared vertices.
- Rooms reference ordered vertex loops.
- Doors/windows anchor to a host wall using a local position and physical width.
- The building footprint and exterior walls are locked.
- Edits are structured transactions applied to a deep copy.
- Shapely validates polygons, intersections, containment, and topology.
- Door connectivity is modeled as a room-access graph from the exterior.
- Low scale or geometry confidence blocks metric edits.
- The source plan changes only when a complete transaction passes validation.

## Implemented operations

- `move_wall`
- `move_opening`
- `add_opening`
- `remove_opening`
- `resize_opening`

## Verified behavior

- A shared-wall move updates both adjacent rooms and keeps openings anchored.
- Locked exterior walls cannot move.
- Collapsed rooms, out-of-footprint rooms, invalid polygons, and overlapping rooms are rejected.
- Every room boundary edge must map to a real wall.
- Openings require an existing host wall, positive width, end clearance, and no overlap.
- Removing the only connecting door is rejected when it makes a room unreachable.
- Multi-operation transactions roll back completely and identify the failed step.
- Preview operations do not mutate the source plan.
- Metric edits are blocked when scale or geometry confidence is below the editing threshold.
- A deterministic 500-offset stress test preserves the 24 m² partition for every accepted shared-wall preview.

## Evidence

Run:

```bash
PYTHONPATH=spikes/001-editor-geometry \
  spikes/001-editor-geometry/venv/Scripts/python.exe \
  -m pytest spikes/001-editor-geometry/tests/test_transactions.py -q
```

Latest result:

```text
19 passed in 0.27s
```

Dependencies are pinned in `requirements-spike.txt`.

## Verdict: PARTIAL

### What worked

The shared-vertex model, immutable previews, wall-hosted openings, global validation, and access-graph checks are viable for orthogonal move/resize/opening operations.

### What did not yet prove production readiness

- Adding/removing walls and splitting/merging room faces are not implemented.
- Wall thickness and finish layers are not modeled.
- Angled and curved wall editing is intentionally unsupported.
- Stable topology and semantic IDs after edge/face splits still require a stronger canonical structure.
- SBC checks are not part of this spike; geometry safety limits are not regulatory claims.

### Recommendation for the real build

Do not copy this spike directly into production. Keep the validated transaction/constraint behavior, but select a topology model that treats edge split, face split, face merge, and opening remapping as first-class operations before implementing the guided editor or Smart Planner generator.
