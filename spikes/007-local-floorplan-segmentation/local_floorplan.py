from __future__ import annotations

import argparse
import json
import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import psutil
import segmentation_models_pytorch as smp
import torch
import yaml
from PIL import Image, ImageDraw
from safetensors.torch import load_file

CLASS_NAMES = ("floor", "wall", "door", "window")
CLASS_COLORS = {
    "floor": (240, 240, 235),
    "wall": (40, 40, 45),
    "door": (230, 120, 50),
    "window": (60, 150, 220),
}
FLOOR_ID = 0
WALL_ID = 1
DOOR_ID = 2
WINDOW_ID = 3
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class PeakRssSampler:
    def __init__(self, interval_seconds: float = 0.01) -> None:
        self.interval_seconds = interval_seconds
        self.process = psutil.Process(os.getpid())
        self.peak_bytes = self.process.memory_info().rss
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.is_set():
            self.peak_bytes = max(self.peak_bytes, self.process.memory_info().rss)
            self._stop.wait(self.interval_seconds)

    def __enter__(self) -> "PeakRssSampler":
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        self._thread.join()
        self.peak_bytes = max(self.peak_bytes, self.process.memory_info().rss)


def load_rgb_image(path: Path) -> Image.Image:
    image = Image.open(path)
    if image.mode == "RGBA":
        white = Image.new("RGBA", image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(white, image)
    return image.convert("RGB")


def prepare_raster(
    image_path: Path,
    image_size: tuple[int, int],
    normalize: bool,
) -> tuple[torch.Tensor, tuple[int, int, int, int], Image.Image]:
    image = load_rgb_image(image_path)
    source_width, source_height = image.size
    target_height, target_width = image_size
    scale = min(target_width / source_width, target_height / source_height)
    inner_width = max(1, int(round(source_width * scale)))
    inner_height = max(1, int(round(source_height * scale)))
    left = (target_width - inner_width) // 2
    top = (target_height - inner_height) // 2

    resized = image.resize((inner_width, inner_height), Image.Resampling.LANCZOS)
    resized_array = np.asarray(resized).copy()
    resized_tensor = torch.from_numpy(resized_array).permute(2, 0, 1).float().div_(255.0)

    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
    if normalize:
        resized_tensor = (resized_tensor - mean) / std
        tensor = torch.zeros(3, target_height, target_width)
    else:
        tensor = mean.expand(3, target_height, target_width).clone()
    tensor[:, top:top + inner_height, left:left + inner_width] = resized_tensor

    background = tuple(int(channel * 255) for channel in IMAGENET_MEAN)
    preview = Image.new("RGB", (target_width, target_height), background)
    preview.paste(resized, (left, top))
    return tensor, (left, top, inner_width, inner_height), preview


def build_model(config: dict, weights_path: Path, device: torch.device) -> torch.nn.Module:
    model = smp.Unet(
        encoder_name=config["model"]["encoder_name"],
        encoder_weights=None,
        in_channels=3,
        classes=len(CLASS_NAMES),
    ).to(device)
    model.load_state_dict(load_file(str(weights_path), device="cpu"))
    model.eval()
    return model


def colorize_mask(mask: np.ndarray) -> Image.Image:
    rgb = np.zeros((*mask.shape, 3), dtype=np.uint8)
    for class_id, class_name in enumerate(CLASS_NAMES):
        rgb[mask == class_id] = CLASS_COLORS[class_name]
    return Image.fromarray(rgb)


def structure_overlay(preview: Image.Image, mask: np.ndarray) -> Image.Image:
    base = np.asarray(preview).copy()
    colors = np.asarray(colorize_mask(mask))
    structural = mask != FLOOR_ID
    blended = base.copy()
    blended[structural] = (
        base[structural].astype(np.float32) * 0.45
        + colors[structural].astype(np.float32) * 0.55
    ).astype(np.uint8)
    return Image.fromarray(blended)


def retain_primary_structure(mask: np.ndarray) -> np.ndarray:
    structure = (mask != FLOOR_ID).astype(np.uint8)
    if not np.any(structure):
        return mask.copy()

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    connected = cv2.morphologyEx(structure, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(connected, 8)
    if count <= 1:
        return mask.copy()

    wall_labels = labels[mask == WALL_ID]
    wall_counts = np.bincount(wall_labels, minlength=count)
    wall_counts[0] = 0
    if np.any(wall_counts):
        primary_label = int(np.argmax(wall_counts))
    else:
        primary_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    cleaned = np.full_like(mask, FLOOR_ID)
    cleaned[labels == primary_label] = mask[labels == primary_label]
    return cleaned


def extract_room_regions(
    mask: np.ndarray,
    *,
    content_rect: tuple[int, int, int, int],
    minimum_area_ratio: float = 0.01,
) -> list[dict]:
    left, top, width, height = content_rect
    barrier = (mask != FLOOR_ID).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    barrier = cv2.morphologyEx(barrier, cv2.MORPH_CLOSE, kernel)
    barrier = cv2.dilate(barrier, kernel, iterations=1)

    traversable = (1 - barrier).astype(np.uint8)
    content = np.zeros_like(traversable)
    content[top:top + height, left:left + width] = 1
    traversable *= content

    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(traversable, 8)
    minimum_area = max(64, int(width * height * minimum_area_ratio))
    content_right = left + width - 1
    content_bottom = top + height - 1
    rooms: list[dict] = []

    for label in range(1, count):
        x, y, w, h, area = (int(value) for value in stats[label])
        touches_content_edge = (
            x <= left
            or y <= top
            or x + w - 1 >= content_right
            or y + h - 1 >= content_bottom
        )
        if touches_content_edge or area < minimum_area:
            continue

        component = (labels == label).astype(np.uint8)
        contours, _hierarchy = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        epsilon = max(1.0, 0.004 * cv2.arcLength(contour, True))
        polygon = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2).astype(int).tolist()
        rooms.append({
            "id": f"room-{len(rooms) + 1}",
            "bbox": {"x": x, "y": y, "width": w, "height": h},
            "area_px": area,
            "polygon": polygon,
        })

    rooms.sort(key=lambda room: (room["bbox"]["y"], room["bbox"]["x"]))
    for index, room in enumerate(rooms, start=1):
        room["id"] = f"room-{index}"
    return rooms


def draw_room_regions(preview: Image.Image, rooms: list[dict]) -> Image.Image:
    canvas = preview.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    for index, room in enumerate(rooms, start=1):
        polygon = [tuple(point) for point in room["polygon"]]
        if len(polygon) >= 3:
            draw.polygon(polygon, fill=(23, 107, 91, 55), outline=(23, 107, 91, 255), width=2)
        bbox = room["bbox"]
        draw.text((bbox["x"] + 4, bbox["y"] + 4), str(index), fill=(0, 0, 0, 255))
    return canvas


def save_binary_mask(mask: np.ndarray, class_id: int, path: Path) -> None:
    Image.fromarray(((mask == class_id) * 255).astype(np.uint8)).save(path)


def run(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    weights_path = Path(args.weights)
    config_path = Path(args.config)
    image_path = Path(args.image)

    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    image_size = tuple(config["data"]["image_size"])
    device = torch.device("cpu")
    initial_rss = psutil.Process(os.getpid()).memory_info().rss

    with PeakRssSampler() as sampler:
        load_started = time.perf_counter()
        model = build_model(config, weights_path, device)
        model_load_seconds = time.perf_counter() - load_started

        image_tensor, content_rect, preview = prepare_raster(
            image_path,
            image_size=image_size,
            normalize=bool(config["data"].get("normalize", True)),
        )
        inference_started = time.perf_counter()
        with torch.inference_mode():
            logits = model(image_tensor.unsqueeze(0).to(device))
            mask = logits.argmax(dim=1).squeeze(0).to("cpu", torch.uint8).numpy()
        inference_seconds = time.perf_counter() - inference_started

    left, top, width, height = content_rect
    cleaned_mask = np.full_like(mask, FLOOR_ID)
    cleaned_mask[top:top + height, left:left + width] = mask[top:top + height, left:left + width]
    raw_mask = cleaned_mask
    mask = retain_primary_structure(raw_mask)
    rooms = extract_room_regions(mask, content_rect=content_rect)

    preview.save(output_dir / "input_letterboxed.png")
    colorize_mask(raw_mask).save(output_dir / "segmentation_mask_raw.png")
    structure_overlay(preview, raw_mask).save(output_dir / "structure_overlay_raw.png")
    colorize_mask(mask).save(output_dir / "segmentation_mask.png")
    structure_overlay(preview, mask).save(output_dir / "structure_overlay.png")
    draw_room_regions(preview, rooms).save(output_dir / "room_regions.png")
    save_binary_mask(mask, WALL_ID, output_dir / "wall_mask.png")
    save_binary_mask(mask, DOOR_ID, output_dir / "door_mask.png")
    save_binary_mask(mask, WINDOW_ID, output_dir / "window_mask.png")

    pixel_count = int(width * height)
    class_pixels = {
        class_name: int((mask[top:top + height, left:left + width] == class_id).sum())
        for class_id, class_name in enumerate(CLASS_NAMES)
    }
    raw_class_pixels = {
        class_name: int((raw_mask[top:top + height, left:left + width] == class_id).sum())
        for class_id, class_name in enumerate(CLASS_NAMES)
    }
    raw_structure_pixels = pixel_count - raw_class_pixels["floor"]
    retained_structure_pixels = pixel_count - class_pixels["floor"]
    result = {
        "model": {
            "architecture": "resnet34-unet",
            "weights_bytes": weights_path.stat().st_size,
            "input_size": list(image_size),
            "device": str(device),
        },
        "source_image": {
            "path": str(image_path),
            "original_size": list(load_rgb_image(image_path).size),
            "content_rect": list(content_rect),
        },
        "performance": {
            "model_load_seconds": round(model_load_seconds, 4),
            "inference_seconds": round(inference_seconds, 4),
            "initial_rss_mb": round(initial_rss / (1024 * 1024), 2),
            "peak_rss_mb": round(sampler.peak_bytes / (1024 * 1024), 2),
        },
        "raw_class_pixels": raw_class_pixels,
        "class_pixels": class_pixels,
        "class_ratios": {
            name: round(count / pixel_count, 6) for name, count in class_pixels.items()
        },
        "postprocessing": {
            "primary_structure_selection": "most_wall_pixels",
            "minimum_room_area_ratio": 0.01,
            "discarded_structure_pixels": raw_structure_pixels - retained_structure_pixels,
        },
        "rooms": rooms,
    }
    (output_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lightweight local floor-plan segmentation spike")
    parser.add_argument("--image", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), ensure_ascii=False, indent=2))
