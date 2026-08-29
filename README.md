# Emad (عماد)

Emad is a local-first floor-plan review demo for nontechnical homeowners. It converts a single-floor image or PDF into a reviewable room model, presents preliminary findings in Arabic, and lets the user preview and approve constrained wall edits through immutable revisions.

> Emad produces preliminary automated observations, not architectural, structural, or Saudi Building Code approval. Measurements, wall structure, and code conclusions must be verified by qualified specialists before construction.

## Current demo workflow

1. Register or sign in.
2. Upload one floor-plan image or single-floor PDF.
3. Extract walls, doors, windows, and deterministic room regions.
4. Attach semantic room labels to the extracted room IDs.
5. Review evidence and preliminary findings.
6. Open the editor and confirm the drawing and scale.
7. Create a temporary wall-move preview.
8. Approve it as a new immutable revision, or discard it.
9. Undo/redo approved revisions and download an HTML report from the current approved revision.

## Architecture

- **Backend:** FastAPI, SQLAlchemy, SQLite, OpenCV, PyTorch, safetensors.
- **Frontend:** Vue 3, Pinia, Vue Router, Vite, Vitest.
- **Local geometry provider:** inference-only CubiCasa parser for walls/openings; room polygons are derived deterministically.
- **Semantic labeling and text planning:** OpenRouter behind role-specific model configuration.
- **Optional external detector:** the preserved Roboflow integration can be selected explicitly. There is no automatic external fallback.
- **Editor safety boundary:** AI may propose a typed operation, but deterministic geometry code creates the preview and validates the revision.

The canonical editor flow is:

```text
Approved revision -> temporary preview -> explicit approval -> immutable revision
                                                |-> undo / redo
```

## Privacy and provider boundary

`FLOOR_PLAN_DETECTOR=local` is the default and does not send the floor plan to Roboflow. Selecting `roboflow` is explicit because it may upload a private plan and consume paid credits.

OpenRouter is currently used for semantic room labeling and AI-assisted edit intent. Do not use real plans with an external provider unless the plan owner has approved that data flow.

## Local model license gate

The current CubiCasa checkpoint is for **non-commercial evaluation and demos**. Its training dataset is licensed under CC BY-NC 4.0. Do not ship these weights in a commercial product without a separate rights review. See [`models/README.md`](models/README.md) for sources, verified hashes, safe conversion, and runtime failure codes.

## Repository layout

```text
backend/app/                 FastAPI application and domain services
backend/tests/               Backend regression and integration tests
frontend/src/                Vue application
frontend/src/views/EditorView.vue
                             Revision-based floor-plan editor
cad_compliance_rag/          Deterministic requirement/rule utilities
models/README.md             Local-model setup and licensing notes
scripts/                     Model setup and verification scripts
spikes/                      Preserved engineering experiments and evidence
```

Runtime data, uploads, generated frontend bundles, caches, and model weights are ignored by Git.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Git
- `uv` is recommended on Windows for creating/installing into virtual environments

## Setup

### 1. Python environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows PowerShell or cmd
.venv\Scripts\activate

# Git Bash
source .venv/Scripts/activate

# macOS/Linux
source .venv/bin/activate
```

Install runtime and test dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

If the virtual environment was created without `pip`, use `uv`:

```bash
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
```

### 2. Local floor-plan model

```bash
pip install -r requirements-model-setup.txt
python scripts/setup_local_floorplan_model.py
```

This downloads the published checkpoint, verifies its checksum, loads it with `weights_only=True`, removes training state, and writes inference tensors to:

```text
models/cubicasa5k-structure.safetensors
```

The generated model file is ignored by Git. Full details are in [`models/README.md`](models/README.md).

### 3. Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Environment

Copy `.env.example` to `.env` and set local values. Never commit `.env`.

Minimum demo configuration:

```env
FLOOR_PLAN_DETECTOR=local
LOCAL_FLOORPLAN_MAX_DIMENSION=512
OPENROUTER_API_KEY=your_local_value
JWT_SECRET_KEY=generate_a_long_random_value
```

Use `LOCAL_FLOORPLAN_MODEL_PATH` only when the safetensors file is stored outside its default location.

## Run

After building the frontend, start the combined application from the repository root:

```bash
python -m backend.app.main
```

Open:

- Application: <http://127.0.0.1:8005>
- API documentation: <http://127.0.0.1:8005/docs>

For frontend development, run `npm run dev` inside `frontend/` while the backend is running.

## Verification

Backend:

```bash
python -m pytest backend/tests -q
```

Frontend tests and production build:

```bash
cd frontend
npm test -- --run
npm run build
```

The verified local acceptance flow covers upload, local detection, semantic labeling, saved project results, editor confirmation, preview, approval, undo, redo, and revision-based report generation.

## Important limitations

- One floor per uploaded image/PDF in the current demo.
- Scale and extracted geometry require user confirmation before metric edits.
- Wall structural status remains unknown unless reviewed independently.
- Door/window editing is not part of the current deterministic editor.
- Room semantics come from an external AI role; geometry does not depend on those labels.
- Findings are preliminary and must not be presented as confirmed violations.
- The current local checkpoint is not cleared for commercial use.

## License

Application code: copyright 2026 Emad. All rights reserved unless a file states otherwise.

Third-party code, models, checkpoints, and datasets retain their own licenses. Review [`models/README.md`](models/README.md) before redistributing or commercializing model artifacts.
