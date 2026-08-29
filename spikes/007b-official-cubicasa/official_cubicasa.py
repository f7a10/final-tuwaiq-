from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np
import psutil
import torch
import torch.nn.functional as F
from PIL import Image

COLORS = {
    "wall": np.array([40, 40, 45], dtype=np.uint8),
    "door": np.array([230, 120, 50], dtype=np.uint8),
    "window": np.array([60, 150, 220], dtype=np.uint8),
}


class PeakRssSampler:
    def __init__(self) -> None:
        self.process = psutil.Process(os.getpid())
        self.peak_bytes = self.process.memory_info().rss
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.is_set():
            self.peak_bytes = max(self.peak_bytes, self.process.memory_info().rss)
            self._stop.wait(0.01)

    def __enter__(self) -> "PeakRssSampler":
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        self._thread.join()
        self.peak_bytes = max(self.peak_bytes, self.process.memory_info().rss)


def load_rgb(path: Path) -> Image.Image:
    image = Image.open(path)
    if image.mode == "RGBA":
        image = Image.alpha_composite(
            Image.new("RGBA", image.size, (255, 255, 255, 255)),
            image,
        )
    return image.convert("RGB")


def prepare_image(path: Path, maximum_dimension: int) -> tuple[torch.Tensor, Image.Image, tuple[int, int]]:
    image = load_rgb(path)
    width, height = image.size
    scale = maximum_dimension / max(width, height)
    resized_width = max(32, int(round(width * scale)))
    resized_height = max(32, int(round(height * scale)))
    canvas_width = ((resized_width + 31) // 32) * 32
    canvas_height = ((resized_height + 31) // 32) * 32

    resized = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
    canvas.paste(resized, (0, 0))
    array = np.asarray(canvas).copy()
    tensor = torch.from_numpy(array).permute(2, 0, 1).float()
    tensor = 2 * (tensor / 255.0) - 1
    return tensor.unsqueeze(0), canvas, (resized_width, resized_height)


def load_model(repo_path: Path, checkpoint_path: Path) -> torch.nn.Module:
    sys.path.insert(0, str(repo_path))
    from floortrans.models.hg_furukawa_original import hg_furukawa_original

    model = hg_furukawa_original(n_classes=44)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model


def make_overlay(
    preview: Image.Image,
    wall_mask: np.ndarray,
    door_mask: np.ndarray,
    window_mask: np.ndarray,
) -> Image.Image:
    result = np.asarray(preview).copy()
    for name, mask in (("wall", wall_mask), ("door", door_mask), ("window", window_mask)):
        result[mask] = (
            result[mask].astype(np.float32) * 0.4
            + COLORS[name].astype(np.float32) * 0.6
        ).astype(np.uint8)
    return Image.fromarray(result)


def save_mask(mask: np.ndarray, path: Path) -> None:
    Image.fromarray((mask * 255).astype(np.uint8)).save(path)


def run(args: argparse.Namespace) -> dict:
    image_path = Path(args.image)
    checkpoint_path = Path(args.checkpoint)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    initial_rss = psutil.Process(os.getpid()).memory_info().rss

    with PeakRssSampler() as sampler:
        load_started = time.perf_counter()
        model = load_model(Path(args.repo), checkpoint_path)
        load_seconds = time.perf_counter() - load_started

        image_tensor, preview, content_size = prepare_image(image_path, args.max_dimension)
        inference_started = time.perf_counter()
        with torch.inference_mode():
            prediction = model(image_tensor)
            prediction = F.interpolate(
                prediction,
                size=image_tensor.shape[-2:],
                mode="bilinear",
                align_corners=False,
            )
        inference_seconds = time.perf_counter() - inference_started

    room_classes = prediction[:, 21:33].softmax(dim=1).argmax(dim=1)[0].cpu().numpy()
    icon_classes = prediction[:, 33:44].softmax(dim=1).argmax(dim=1)[0].cpu().numpy()
    content_width, content_height = content_size
    content_slice = np.zeros_like(room_classes, dtype=bool)
    content_slice[:content_height, :content_width] = True
    wall_mask = (room_classes == 2) & content_slice
    window_mask = (icon_classes == 1) & content_slice
    door_mask = (icon_classes == 2) & content_slice

    preview.save(output_dir / "input.png")
    save_mask(wall_mask, output_dir / "wall_mask.png")
    save_mask(door_mask, output_dir / "door_mask.png")
    save_mask(window_mask, output_dir / "window_mask.png")
    make_overlay(preview, wall_mask, door_mask, window_mask).save(output_dir / "overlay.png")

    result = {
        "model": {
            "architecture": "cubicasa-hourglass-multitask",
            "parameters": sum(parameter.numel() for parameter in model.parameters()),
            "checkpoint_bytes": checkpoint_path.stat().st_size,
            "input_size": list(image_tensor.shape[-2:]),
            "max_dimension": args.max_dimension,
            "device": "cpu",
        },
        "performance": {
            "model_load_seconds": round(load_seconds, 4),
            "inference_seconds": round(inference_seconds, 4),
            "initial_rss_mb": round(initial_rss / (1024 * 1024), 2),
            "peak_rss_mb": round(sampler.peak_bytes / (1024 * 1024), 2),
        },
        "pixels": {
            "wall": int(wall_mask.sum()),
            "door": int(door_mask.sum()),
            "window": int(window_mask.sum()),
        },
    }
    (output_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-dimension", type=int, choices=(256, 512), required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), indent=2))
