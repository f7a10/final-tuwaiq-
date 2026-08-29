# 007b: Official CubiCasa Multi-Task Parser Comparison

## Question

Does the official CubiCasa multi-task parser improve door/window separation enough to justify its older code and larger checkpoint compared with the compact four-class ResNet-34 U-Net?

## Scope

This is a standalone comparison. It does not modify the production pipeline. Although the official model predicts semantic room classes, this spike ignores those classes and uses only:

- wall segmentation
- door segmentation
- window segmentation

Room type labeling remains an LLM responsibility, and geometry remains deterministic.

## Candidate

- Architecture: CubiCasa hourglass multi-task parser
- Parameters: 17,354,456 (about 66.2 MiB in FP32)
- Checkpoint: 208,651,193 bytes, including optimizer/training state
- Training data: CubiCasa5K (`CC BY-NC 4.0`)
- Legacy reference environment: Python 3.6 / PyTorch 1.0
- Test environment: Python 3.11 / PyTorch CPU

The checkpoint is loaded with `weights_only=True`; unsafe Pickle execution is not enabled.

## Comparison outputs

For each input size, the script writes:

- `input.png`
- `wall_mask.png`
- `door_mask.png`
- `window_mask.png`
- `overlay.png`
- `result.json`

## Verdict: SELECTED FOR THE LOCAL DEMO PATH

The 512-pixel official parser was selected over the compact four-class model for the non-commercial local demo path because it separated doors and windows substantially better while retaining acceptable CPU performance. On the reference sample it produced five wall-bounded regions, correctly kept the dashed lower-left area within the open-plan room, and rejected the detached title banner after primary-wall-network filtering.

Reference CPU result at 512 maximum dimension:

- inference: approximately 0.36 seconds
- peak process RSS: approximately 615 MB
- raw training checkpoint: 208,651,193 bytes
- inference-only safetensors export: approximately 69.6 MB

The model is not approved for commercial production. CubiCasa5K training data is licensed CC BY-NC 4.0; production requires a separate rights review or weights trained on commercially usable data.
