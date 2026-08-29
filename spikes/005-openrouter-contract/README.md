# Spike 005: Schema-Constrained OpenRouter Edit Intent

## Question

Can Emad accept model-produced edit intent without allowing the model to write geometry, bypass validation, or mutate an approved revision directly?

## Scope

- Strict JSON envelope with a versioned schema.
- Exact base revision reference.
- Whitelisted typed editor commands using integer millimetres.
- Explicit typed clarification state for unresolved ambiguity.
- Unknown keys, command types, units, and geometry payloads are rejected.
- Valid intent can create an editor Preview transaction only.
- OpenRouter structured-output request options are generated dynamically for the current revision.
- No API key, automatic approval, or production network integration in this spike.

## Evidence

The contract suite passes 8 tests. The complete editor, planner, and contract gate passes:

```text
62 passed in 0.43s
```

`compileall` and `git diff --check` also pass.

Validated behaviors include:

- a valid model envelope becomes typed commands and an immutable DCEL Preview;
- the approved source revision is unchanged by Preview generation;
- only `move_wall` and `move_opening` are available in the V1 schema;
- commands use stable IDs and integer millimetres, never model-authored vertices or polygons;
- duplicate JSON keys are rejected before normalization;
- malformed clarification values are rejected cleanly rather than raising an exception;
- a valid ambiguity becomes one typed `Clarification` question and cannot create a Preview;
- clarification fields are checked locally with exact-key validation;
- only one clarification question is allowed per turn;
- model command batches are capped at 20 operations;
- the OpenRouter request fragment uses strict JSON Schema and requires compatible provider parameters;
- the `base_revision_id` is constrained in both the provider schema and the local validator;
- a non-ready intent never reaches the editor transaction kernel.

## OpenRouter Contract

The request fragment follows the current official OpenRouter structured-output format:

```text
response_format.type = json_schema
response_format.json_schema.strict = true
provider.require_parameters = true
```

Reference: https://openrouter.ai/docs/guides/features/structured-outputs

Local validation remains mandatory because OpenRouter documents that enforcement can vary by provider endpoint.

## Verdict: VALIDATED

The contract boundary is viable for Emad V2. OpenRouter can interpret homeowner language into a small typed intent envelope, while canonical geometry, safety validation, Preview creation, and approval remain deterministic local responsibilities.

## Production Recommendation

Retain this boundary:

```text
Homeowner request
  -> OpenRouter structured output
  -> duplicate-key-safe JSON parse
  -> exact local schema validation
  -> stale-base check
  -> typed editor commands OR one clarification
  -> atomic DCEL Preview
  -> measured impact and warnings
  -> explicit homeowner approval
  -> committed Revision
```

The application must never execute model-authored coordinates, polygons, SQL, shell commands, arbitrary operation names, or an `apply_immediately` instruction. Schema support must be checked per selected endpoint, and routing should require structured-output support.

## Known Limits

- This spike does not make a live OpenRouter call.
- Model selection, retries, rate limits, cost controls, response refusal handling, and observability remain production integration work.
- Only wall and opening movement commands are exposed in this first contract.
- Add/remove opening, split/merge room, and planner requests require separately versioned schema additions and tests.
- The local parser is a focused spike implementation, not a general JSON Schema engine.
- User-facing Arabic question wording and accessibility are validated in the next editor UX stage.
