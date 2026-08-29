import hashlib
import tempfile
import unittest
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import load_file

from scripts.setup_local_floorplan_model import ModelSetupError, export_checkpoint


class LocalModelSetupTests(unittest.TestCase):
    def test_checkpoint_hash_is_verified_before_export(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "model.pkl"
            output = Path(directory) / "model.safetensors"
            checkpoint.write_bytes(b"not-a-checkpoint")

            with self.assertRaisesRegex(ModelSetupError, "checkpoint_checksum_mismatch"):
                export_checkpoint(
                    checkpoint,
                    output,
                    expected_checkpoint_sha256="0" * 64,
                )

            self.assertFalse(output.exists())

    def test_model_state_is_exported_as_safe_inference_tensors(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "model.pkl"
            output = Path(directory) / "model.safetensors"
            torch.save(
                {
                    "model_state": {
                        "layer.weight": torch.tensor([[1.0, 2.0]]),
                        "layer.bias": torch.tensor([3.0]),
                    },
                    "optimizer_state": {"must_not_ship": True},
                },
                checkpoint,
            )
            digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()

            output_digest = export_checkpoint(
                checkpoint,
                output,
                expected_checkpoint_sha256=digest,
            )

            tensors = load_file(str(output), device="cpu")
            self.assertEqual(set(tensors), {"layer.weight", "layer.bias"})
            self.assertEqual(tensors["layer.bias"].tolist(), [3.0])
            self.assertEqual(output_digest, hashlib.sha256(output.read_bytes()).hexdigest())
            del tensors
            with safe_open(str(output), framework="pt", device="cpu") as handle:
                self.assertEqual(handle.metadata()["license"], "CC-BY-NC-4.0")

    def test_export_rejects_an_unexpected_tensor_payload_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "model.pkl"
            output = Path(directory) / "model.safetensors"
            torch.save({"model_state": {"weight": torch.tensor([1.0])}}, checkpoint)
            digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()

            with self.assertRaisesRegex(
                ModelSetupError,
                "inference_tensor_checksum_mismatch",
            ):
                export_checkpoint(
                    checkpoint,
                    output,
                    expected_checkpoint_sha256=digest,
                    expected_tensor_data_sha256="0" * 64,
                )

            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
