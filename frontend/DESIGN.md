# Emad Product Interface

## Product promise

Emad helps a non-technical homeowner understand a single-floor residential plan, review evidence-backed potential issues, compare coordinated modernization options, and approve reversible edits. It does not replace a licensed architect or issue authoritative compliance decisions.

## Primary journey

1. **Configure — New plan (`/`)**
   - Upload one PDF, PNG, or JPG plan, up to 10 MB.
   - Name the project.
   - State clearly that results are preliminary guidance.
2. **Monitor — Analysis (`/projects/:id`)**
   - Show actual processing state without simulated timers.
   - Distinguish provider/configuration failure from `not_detected` and `not_verifiable`.
3. **Inspect — Project report (`/projects/:id`)**
   - Keep the plan and evidence primary.
   - Use “potential issue” rather than “confirmed violation” until expert validation exists.
   - Show confidence, source, observed value, expected value, and verification limits.
4. **Operate — Editor (`/projects/:id/editor`)**
   - Select a room, wall, door, or window.
   - Every request creates a Preview; AI never commits geometry directly.
   - Compare before/after, approve explicitly, create an immutable Revision, and support Undo/Redo.
5. **Explore — Projects (`/projects`)**
   - Search and filter real projects without invented metrics.

## Visual system

- Arabic-first RTL interface using IBM Plex Sans Arabic.
- Warm neutral canvas (`--emad-bg`) and quiet white surfaces.
- Green means approved/current state.
- Blue means temporary Preview.
- Amber means warning or specialist review.
- Red means failure or destructive action.
- Color is never the only status signal; pair it with text, line style, or an icon.
- Use one-pixel borders, restrained shadows, and moderate radii.
- No decorative gradients, glassmorphism, fake statistics, or equal-weight feature-card grids.

## Interaction rules

- Minimum interactive target: 44 px.
- Visible focus rings for keyboard navigation.
- Respect `prefers-reduced-motion`.
- Preserve user input when validation fails.
- Do not use browser alerts for workflow errors.
- Do not show a successful engineering result when an external service fails.
- Metric edits require confirmed scale; low confidence may allow Preview but blocks approval.
- Structural, exterior, and unknown-status walls remain locked by default.

## AI boundary

- OpenRouter interprets homeowner language, explains evidence, and proposes typed intent.
- Specialized OCR/CV detects plan primitives and provides evidence with confidence.
- Deterministic geometry code owns coordinates, topology, measurements, validation, Preview, and Revision creation.
- AI output must conform to a strict versioned schema and may only request whitelisted operations against stable IDs.
- Missing credentials, provider errors, and uncertain evidence remain explicit states.

## Responsive order

On narrow screens, preserve the task sequence:

1. Selection
2. Plan
3. Edit action / Preview review

Avoid horizontal page scrolling; tool strips may scroll independently when necessary.
