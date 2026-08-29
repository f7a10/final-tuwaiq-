# Spike 004: Deterministic Repair Candidate Planner

## Question

Can Emad generate, validate, score, and select three genuinely different coordinated repair candidates deterministically, using the editor DCEL transaction kernel rather than a second geometry model?

## Scope

- Start from an existing valid `PlanRevision`.
- Enumerate bounded shared-wall moves on an integer-millimetre lattice.
- Coordinate required opening movements with each wall repair in one transaction.
- Treat geometry, reachability, configured room minima, and opening requirements as hard feasibility gates.
- Measure all soft scores from validated candidate geometry.
- Select Minimal, Balanced, and Priority profiles with stable tie-breaking.
- Enforce a minimum diversity distance rather than cloning or relabelling candidates.
- Record request, rule-pack, engine, seed, and budget metadata.
- Make zero network, OpenRouter, or RAG calls during planning.

## Evidence

The planner suite passes 7 tests. The combined editor and planner gate passes:

```text
54 passed in 0.43s
```

`compileall` and `git diff --check` also pass.

Validated behaviors include:

- identical canonical request inputs produce identical candidate JSON, hashes, scores, and ordering;
- candidates are real immutable DCEL revisions accepted by the editor validator;
- Minimal, Balanced, and Priority select different verified candidates in the fixture;
- wall and opening repairs are coordinated in one atomic transaction;
- source revisions remain unchanged;
- impossible aggregate room minima return `infeasible_proven` from presolve with an actionable area conflict;
- partial search with a feasible result returns `feasible_budget_limited`, not false low diversity or false infeasibility;
- a fully searched but too-similar pool returns `insufficient_diversity` and never duplicates candidates;
- unknown room, wall, or required-opening references return `needs_clarification` before search;
- all scoring and explanations are derived from measured geometry and versioned request metadata.

## Verdict: VALIDATED

The deterministic repair-planner architecture is viable for Emad V2. It can coordinate multiple editor commands, reject unsafe candidates through the same canonical kernel, and return honestly labelled search outcomes without relying on an LLM for geometry or ranking.

## Production Recommendation

Retain this separation:

```text
PlannerRequest
  -> canonicalization and request hash
  -> presolve and clarification diagnostics
  -> deterministic candidate enumeration/search
  -> atomic editor transactions
  -> independent validation
  -> hard-feasibility filtering
  -> measured score components
  -> diversity filtering
  -> Minimal / Balanced / Priority selection
```

Candidate IDs must continue to include canonical plan geometry, request hash, rule-pack version, engine version, seed, and search budget. A candidate is publishable only when hard violations and skipped hard rules are both zero.

## Known Limits

- This spike repairs an existing two-room rectilinear plan; it is not a general from-scratch home generator.
- The search operator is a bounded shared-wall move plus required opening moves.
- Diversity is represented by wall displacement in this narrow fixture; production diversity must also compare adjacency graphs, circulation topology, and room centroids.
- Scoring currently demonstrates movement cost, area dissatisfaction, and one room priority. Construction quantities, plumbing, daylight, privacy, circulation, and compliance slack remain later objectives.
- The prototype area constraints are not reviewed SBC thresholds.
- CP-SAT cell decomposition, fixed solids, explicit circulation, and non-rectilinear footprints remain future stages.
- OpenRouter requirement extraction is deliberately outside this spike and is tested by the next contract spike.
