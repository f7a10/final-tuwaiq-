# Spike 003: Immutable DCEL Revisions

## Question

Can a constrained half-edge/DCEL model provide deterministic, immutable floor-plan revisions while preserving the validated behavior from the earlier geometry spikes?

## Scope

- Integer millimetre coordinates.
- Straight, orthogonal, noded wall segments for the initial editor scope.
- One exterior face and bounded room faces.
- Twin half-edges with explicit `next`, `prev`, `face`, and stable wall-run references.
- Openings anchored by metric station on stable wall runs.
- Append-only revisions with parent IDs, command logs, canonical serialization, and hashes.
- Shapely/polygonize is used as a differential validator, not canonical editable state.

## Evidence

The Spike 003 suite passes 21 tests. The combined geometry gate across Spikes 001–003 passes:

```text
47 passed in 0.35s
```

`compileall` and `git diff --check` also pass.

Validated behaviors include:

- immutable source revisions and deterministic child hashes;
- stale-base IDs in command entry points;
- shared-wall movement with stable room identities;
- stable wall runs spanning multiple noded half-edge pairs;
- direct DCEL split and merge operations;
- wall noding without changing wall-run identity or opening position;
- compound split-by-wall-stations committed as one atomic revision;
- atomic multi-command commit and full rollback with failing-operation index;
- wall-hosted opening add, move, and remove operations;
- opening edge clearance and overlap rejection;
- room minimum-span rejection;
- explicit half-edge twin, next/previous, face, support, and geometric-continuity checks;
- differential agreement between DCEL faces, wall polygonization, and footprint;
- reachability from the exterior through doors;
- rejection of isolated rooms and removal of the only connecting door;
- rejection of no-op edits that would pollute revision history.

## Verdict: VALIDATED

A constrained DCEL with stable wall runs is a viable canonical foundation for Emad V2's first editor. The successful spike code remains disposable; production code should preserve its invariants and tests rather than copy the module blindly.

## Production Recommendation

Use this ownership model:

```text
PlanRevision
  -> vertices in integer millimetres
  -> stable WallRuns
  -> noded twin HalfEdges
  -> exterior and bounded Face cycles
  -> wall-anchored Openings
  -> atomic typed Commands
  -> canonical hash and parent revision
```

Room polygons and measurements must be derived from face cycles. Shapely should remain an import, diagnostics, and differential-validation tool—not editable canonical state.

The planner and natural-language layers must emit typed commands against this model. They must never write final polygons or pixels directly.

## Known Limits

- The spike exercises straight orthogonal walls; angled-wall editing needs a separate acceptance gate.
- Curved walls, multiple exterior components, holes/courtyards, shafts, columns, and wall thickness are not modeled yet.
- Clear usable area and finish offsets are not modeled.
- Persistence, database locking, and multi-user conflict resolution are not implemented; only stale base revision checks are represented.
- Importing noisy OCR/CV geometry into a valid DCEL still needs a dedicated normalization pipeline.
- `800mm` room span and `200mm` opening clearance are prototype geometry safeguards, not cited SBC requirements.
- Structural safety and regulatory compliance remain separate reviewed rule packs and must not be inferred from this topology.

These limits do not block the deterministic planner spike because it will use the same restricted V1 geometry envelope.
