# 007: Lightweight Local Floor-Plan Segmentation

## Question

Given a real PNG floor plan, when a compact local segmentation model runs on CPU, does it produce useful masks for walls, doors, windows, and room regions without using Roboflow?

## Scope

This is a throwaway feasibility spike. It does not modify the production `SmartArchitect` pipeline or remove the Roboflow implementation.

Room semantic types are intentionally out of scope. A later LLM stage may label bounded room crops, but it must not create or modify geometry.

## Candidate

- Architecture: ResNet-34 U-Net
- Input: aspect-preserving 512×512 RGB
- Output classes: floor, wall, door, window
- Weights: `Yytsi/floorplan-to-3d-walls` (`best.safetensors`, 97,851,168 bytes)
- Runtime: PyTorch CPU for this spike
- Source code license: MIT
- Training data provenance: CubiCasa5K (`CC BY-NC 4.0`)

The CubiCasa5K non-commercial restriction means this candidate is suitable for evaluation and the current non-commercial demo, but it is not automatically approved for a future commercial release. Production weights require a separate licensing/data decision.

## Observable outputs

Running `segment_floorplan.py` creates:

- `input_letterboxed.png`
- `segmentation_mask.png`
- `structure_overlay.png`
- `room_regions.png`
- `wall_mask.png`
- `door_mask.png`
- `window_mask.png`
- `result.json`

`result.json` records model size, CPU inference time, approximate process peak RSS, class pixel ratios, and deterministically extracted room regions.

## Safety and rollback

The real integration, if validated, should use a provider boundary:

```text
FLOOR_PLAN_DETECTOR=local | roboflow
```

Roboflow remains implemented and tested. It should not be commented out or duplicated. Switching the environment value is the rollback.

## Run

```bash
python segment_floorplan.py \
  --image ../../test_plan_real.png \
  --weights %LOCALAPPDATA%/Temp/emad-local-floorplan-model/best.safetensors \
  --config %LOCALAPPDATA%/Temp/emad-local-floorplan-model/config.yaml \
  --output output
```

## Verdict: PENDING

The verdict will be updated only after inspecting the generated overlays and recording actual CPU measurements on `test_plan_real.png`.
