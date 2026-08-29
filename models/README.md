# Local Floor-Plan Model

Emad uses an inference-only CubiCasa parser for the **local, non-commercial demo path**. The model extracts wall regions, doors, windows, and deterministic room polygons. It does not assign room types; OpenRouter may attach a semantic label only to an existing room ID.

## License gate

The upstream CubiCasa5K repository and published checkpoint were trained from CubiCasa5K data licensed under **CC BY-NC 4.0**. Use this checkpoint only for non-commercial evaluation and demos. Do not ship it in a commercial product without a separate rights review. Commercial production should use weights trained on data with suitable commercial rights.

Upstream sources:

- Repository: <https://github.com/CubiCasa/CubiCasa5k>
- Published checkpoint: <https://drive.google.com/file/d/1gRB7ez1e4H7a9Y09lLqRuna0luZO5VRK/view>
- Dataset/license record: <https://zenodo.org/records/2613548>

## Setup

From the project root:

```bash
pip install -r requirements.txt
pip install -r requirements-model-setup.txt
python scripts/setup_local_floorplan_model.py
```

The setup script:

1. Downloads the official training checkpoint.
2. Verifies its SHA-256 checksum before deserialization.
3. Loads it with `torch.load(..., weights_only=True)`.
4. discards optimizer/training state.
5. Writes only inference tensors in non-executable `safetensors` format.
6. Deletes the downloaded Pickle checkpoint unless `--keep-checkpoint` is specified.

Expected files and hashes:

| Artifact | SHA-256 |
|---|---|
| Official checkpoint file | `dd20b4e1bf1d670f2125107b079df06958b1ccd36e49a464ab739aeb00b8e7a2` |
| Inference tensor payload | `b153ebb521eecfa3908822218d23e5374896a4b21ad7929861bb4714047f5cd1` |

The complete safetensors file hash may differ between exports because metadata key ordering is not stable. The setup script therefore verifies the required metadata and the deterministic tensor payload separately.

The generated file is:

```text
models/cubicasa5k-structure.safetensors
```

Model files are ignored by Git. Do not commit either the checkpoint or the generated weights.

To convert an already downloaded official checkpoint:

```bash
python scripts/setup_local_floorplan_model.py --checkpoint C:/path/to/model_best_val_loss_var.pkl --force
```

## Provider selection

The local provider is the default:

```env
FLOOR_PLAN_DETECTOR=local
LOCAL_FLOORPLAN_MAX_DIMENSION=512
```

To select the preserved Roboflow integration explicitly:

```env
FLOOR_PLAN_DETECTOR=roboflow
ROBOFLOW_API_KEY=your-local-env-value
```

There is intentionally no silent fallback from local processing to Roboflow. An external fallback could upload a private plan and consume paid credits without the user's knowledge.

## Runtime failure codes

- `local_model_missing`
- `local_model_load_failed`
- `local_detection_failed`
- `wall_detection_empty`
- `room_detection_empty`

All failures are fail-closed: the project is marked failed and receives no compliance score.
