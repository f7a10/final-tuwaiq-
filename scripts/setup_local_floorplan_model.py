"""Download and safely convert the official CubiCasa demo checkpoint.

The original training checkpoint is verified before torch deserialization and is
loaded with ``weights_only=True``. Only model tensors are exported to the
non-executable safetensors format used by the application.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from pathlib import Path

import torch
from safetensors.torch import save_file

OFFICIAL_FILE_ID = "1gRB7ez1e4H7a9Y09lLqRuna0luZO5VRK"
OFFICIAL_CHECKPOINT_SHA256 = "dd20b4e1bf1d670f2125107b079df06958b1ccd36e49a464ab739aeb00b8e7a2"
INFERENCE_TENSOR_DATA_SHA256 = "b153ebb521eecfa3908822218d23e5374896a4b21ad7929861bb4714047f5cd1"
INFERENCE_MODEL_METADATA = {
    "source": "CubiCasa/CubiCasa5k",
    "source_commit": "c34440266665a11f4484eb06cd2e4b7d72ad76c1",
    "license": "CC-BY-NC-4.0",
    "purpose": "non-commercial evaluation/demo",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "models" / "cubicasa5k-structure.safetensors"


class ModelSetupError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_inference_model(
    path: Path,
    *,
    expected_tensor_data_sha256: str,
) -> str:
    try:
        with Path(path).open("rb") as source:
            header_size_bytes = source.read(8)
            if len(header_size_bytes) != 8:
                raise ValueError("short_header")
            header_size = struct.unpack("<Q", header_size_bytes)[0]
            header = json.loads(source.read(header_size))
            if header.get("__metadata__") != INFERENCE_MODEL_METADATA:
                raise ValueError("metadata_mismatch")
            digest = hashlib.sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except (OSError, ValueError, json.JSONDecodeError, struct.error) as error:
        raise ModelSetupError("inference_model_validation_failed") from error
    tensor_digest = digest.hexdigest()
    if tensor_digest != expected_tensor_data_sha256.lower():
        raise ModelSetupError("inference_tensor_checksum_mismatch")
    return tensor_digest


def export_checkpoint(
    checkpoint_path: Path,
    output_path: Path,
    *,
    expected_checkpoint_sha256: str,
    expected_tensor_data_sha256: str | None = None,
) -> str:
    checkpoint_path = Path(checkpoint_path)
    output_path = Path(output_path)
    if not checkpoint_path.is_file():
        raise ModelSetupError("checkpoint_missing")
    if sha256_file(checkpoint_path) != expected_checkpoint_sha256.lower():
        raise ModelSetupError("checkpoint_checksum_mismatch")

    try:
        checkpoint = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=True,
        )
        model_state = checkpoint["model_state"]
        if not isinstance(model_state, dict) or not model_state:
            raise KeyError("model_state")
        tensors = {
            str(name): tensor.detach().cpu().contiguous()
            for name, tensor in model_state.items()
            if isinstance(tensor, torch.Tensor)
        }
        if len(tensors) != len(model_state):
            raise TypeError("non_tensor_model_state")
    except Exception as error:
        raise ModelSetupError("checkpoint_export_failed") from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output_path.with_suffix(output_path.suffix + ".part")
    try:
        save_file(tensors, str(temporary_output), metadata=INFERENCE_MODEL_METADATA)
        output_digest = sha256_file(temporary_output)
        if expected_tensor_data_sha256:
            validate_inference_model(
                temporary_output,
                expected_tensor_data_sha256=expected_tensor_data_sha256,
            )
        os.replace(temporary_output, output_path)
    finally:
        temporary_output.unlink(missing_ok=True)
    return output_digest


def download_official_checkpoint(destination: Path) -> Path:
    try:
        import gdown
    except ImportError as error:
        raise ModelSetupError("gdown_not_installed") from error

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_download = destination.with_suffix(destination.suffix + ".part")
    temporary_download.unlink(missing_ok=True)
    downloaded = gdown.download(
        id=OFFICIAL_FILE_ID,
        output=str(temporary_download),
        quiet=False,
    )
    if not downloaded or not temporary_download.is_file():
        temporary_download.unlink(missing_ok=True)
        raise ModelSetupError("checkpoint_download_failed")
    os.replace(temporary_download, destination)
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the local CubiCasa inference model safely.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Use an existing official checkpoint instead of downloading it.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--keep-checkpoint", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    if output.is_file() and not args.force:
        validate_inference_model(
            output,
            expected_tensor_data_sha256=INFERENCE_TENSOR_DATA_SHA256,
        )
        print(f"Local model is ready: {output}")
        print(f"File SHA256: {sha256_file(output)}")
        print(f"Tensor payload SHA256: {INFERENCE_TENSOR_DATA_SHA256}")
        return 0

    downloaded_checkpoint = args.checkpoint is None
    checkpoint = (
        (PROJECT_ROOT / "models" / ".cubicasa-model.pkl")
        if downloaded_checkpoint
        else args.checkpoint.resolve()
    )
    if downloaded_checkpoint:
        print("Downloading the official CubiCasa non-commercial demo checkpoint...")
        download_official_checkpoint(checkpoint)

    try:
        output_digest = export_checkpoint(
            checkpoint,
            output,
            expected_checkpoint_sha256=OFFICIAL_CHECKPOINT_SHA256,
            expected_tensor_data_sha256=INFERENCE_TENSOR_DATA_SHA256,
        )
    finally:
        if downloaded_checkpoint and not args.keep_checkpoint:
            checkpoint.unlink(missing_ok=True)

    print(f"Local model is ready: {output}")
    print(f"File SHA256: {output_digest}")
    print(f"Tensor payload SHA256: {INFERENCE_TENSOR_DATA_SHA256}")
    print("License gate: non-commercial demo/evaluation only (CC BY-NC 4.0 training data).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ModelSetupError as error:
        print(f"Model setup failed: {error}")
        raise SystemExit(1) from error
