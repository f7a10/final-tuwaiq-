# ==========================================
# SmartArchitect ML Analysis Service
# Integrated with CAD Compliance RAG + Grok 3
# ==========================================

import cv2
import base64
import json
import numpy as np

from backend.app.config import (
    FLOOR_PLAN_DETECTOR,
    LOCAL_FLOORPLAN_MAX_DIMENSION,
    LOCAL_FLOORPLAN_MODEL_PATH,
    OPENROUTER_API_KEY,
    OPENROUTER_ASSISTANT_MODEL,
    OPENROUTER_FALLBACK_MODELS,
    OPENROUTER_PLANNING_MODEL,
    OPENROUTER_VISION_MODEL,
    PROJECT_ROOT,
    ROBOFLOW_API_KEY,
)
from backend.app.services.ai_provider import OpenRouterProvider, ProviderModels
from backend.app.services.floorplan_detector import (
    FloorPlanDetectorError,
    build_floorplan_detector,
)
from backend.app.services.plan_ingestion import prepare_floor_plan

# Import CAD Compliance RAG
import sys
sys.path.insert(0, PROJECT_ROOT)
from cad_compliance_rag.src.analyze_plan import analyze_plan

# Engineering settings
PIXELS_PER_METER = 100.0  # Default scale
WINDOW_PADDING = 25       # Pixels to expand search area for windows


class AnalysisPipelineError(RuntimeError):
    """Raised when a required analysis stage cannot produce reliable evidence."""


# Room type mapping: AI output -> cad_compliance_rag types
ROOM_TYPE_MAP = {
    "bedroom": "Bedroom",
    "master bedroom": "Bedroom",
    "bedroom #1": "Bedroom",
    "bedroom #2": "Bedroom", 
    "bedroom #3": "Bedroom",
    "kids room": "Bedroom",
    "guest room": "Bedroom",
    "living room": "Living",
    "living": "Living",
    "family room": "Living",
    "salon": "Living",
    "majlis": "Living",
    "مجلس": "Living",
    "kitchen": "Kitchen",
    "مطبخ": "Kitchen",
    "bathroom": "Bathroom",
    "bath": "Bathroom",
    "master bath": "Bathroom",
    "washroom": "Bathroom",
    "wc": "WC",
    "toilet": "WC",
    "half bath": "WC",
    "powder room": "WC",
    "corridor": "Corridor",
    "hallway": "Corridor",
    "hall": "Corridor",
    "dining room": "Living",  # Map to Living for compliance
    "dining": "Living",
    "dinning area": "Living",
    "open plan kitchen/living": "Living",  # Treat as Living for min area
    "closet": "ServiceRoom",
    "storage": "ServiceRoom",
    "laundry": "ServiceRoom",
    "utility": "ServiceRoom",
    "service room": "ServiceRoom",
    "service room": "ServiceRoom",
    "unknown": "Unknown",
    "great room": "Living",
    "lounge": "Living",
    "sitting room": "Living",
    "drawing room": "Living",
    "reception": "Living",
    "entrance": "Corridor",
    "foyer": "Corridor",
    "lobby": "Corridor",
    "pantry": "Kitchen",
    "dirty kitchen": "Kitchen",
    "kitchenette": "Kitchen",
    "cook": "Kitchen",
}


def normalize_room_type(raw_type: str) -> str:
    """Normalize AI-detected room type to cad_compliance_rag format."""
    raw_lower = raw_type.lower().strip()
    return ROOM_TYPE_MAP.get(raw_lower, "Unknown")


def calculate_dynamic_scale(structure_predictions, default_scale=100.0):
    """Calculate pixels per meter based on detected door widths."""
    doors = []
    for item in structure_predictions:
        if "door" in item['class'].lower() and "double" not in item['class'].lower():
            doors.append(item['width'])
    
    if not doors:
        return default_scale
    
    avg_door_pixel_width = sum(doors) / len(doors)
    new_scale = avg_door_pixel_width / 0.9  # Standard door width ~0.9m
    
    print(f"Auto-Calibration: Found {len(doors)} doors. Scale: {new_scale:.2f} px/m")
    return new_scale


def calculate_proposed_fix(room_box, rule_id, expected_str, current_metrics, scale):
    """
    Calculate a proposed schematic fix for a violation.
    Returns a dictionary with 'type', 'box' (normalized), and 'description'.
    """
    import re
    
    # Parse target value from expected string (e.g., "area_sqm >= 12.0")
    m = re.search(r">=\s*([0-9.]+)", expected_str or "")
    if not m:
        return None
        
    target_val = float(m.group(1))
    
    # Current dimensions in meters
    w_m = current_metrics['width']
    h_m = current_metrics['height']
    
    # Current box in normalized coords
    bx, by, bw, bh = room_box['x'], room_box['y'], room_box['w'], room_box['h']
    
    new_w_m, new_h_m = w_m, h_m
    description = ""
    
    if "MIN-AREA" in rule_id:
        # Expand proportionally to meet area
        current_area = w_m * h_m
        if current_area <= 0: return None
        ratio = (target_val / current_area) ** 0.5
        new_w_m = w_m * ratio
        new_h_m = h_m * ratio
        description = f"Expand room area to {target_val}m²"
        
    elif "MIN-WIDTH" in rule_id:
        # Expand smallest dimension to target width
        if w_m < target_val:
            new_w_m = target_val
            description = f"Widen room to {target_val}m"
        elif h_m < target_val:
            new_h_m = target_val
            description = f"Widen room to {target_val}m"
        else:
            return None # Already wide enough?
            
    elif "HAS-WINDOW" in rule_id:
        # For window violations, we highlight the room and suggest installation
        # Since we can't easily know exterior walls, we highlight the room itself.
        description = "Install Window (Natural Vent.)"
        return {
            "type": "installation",
            "description": description,
            "box": room_box,
            "targetValue": 0
        }

    else:
        return None # No fix logic for this rule yet

    # Calculate new normalized box dimensions
    # Assuming we expand from the center
    cx = bx + bw/2
    cy = by + bh/2
    
    scale_factor_w = new_w_m / w_m if w_m > 0 else 1
    scale_factor_h = new_h_m / h_m if h_m > 0 else 1
    
    new_bw = bw * scale_factor_w
    new_bh = bh * scale_factor_h
    
    new_bx = cx - new_bw/2
    new_by = cy - new_bh/2
    
    return {
        "type": "expansion",
        "description": description,
        "box": {
            "x": round(new_bx, 4),
            "y": round(new_by, 4),
            "w": round(new_bw, 4),
            "h": round(new_bh, 4)
        },
        "targetValue": target_val
    }


class SmartArchitect:
    """Full analysis class for floor plan processing with CAD Compliance RAG."""
    
    def __init__(self, *, detector=None, ai_provider=None):
        print("Initializing SmartArchitect...")
        self.ai_provider = ai_provider or OpenRouterProvider(
                api_key=OPENROUTER_API_KEY,
                models=ProviderModels(
                    vision=OPENROUTER_VISION_MODEL,
                    planning=OPENROUTER_PLANNING_MODEL,
                    assistant=OPENROUTER_ASSISTANT_MODEL,
                    fallbacks=OPENROUTER_FALLBACK_MODELS,
                ),
            )
        self.detector = detector or build_floorplan_detector(
            provider=FLOOR_PLAN_DETECTOR,
            local_model_path=LOCAL_FLOORPLAN_MODEL_PATH,
            local_max_dimension=LOCAL_FLOORPLAN_MAX_DIMENSION,
            roboflow_api_key=ROBOFLOW_API_KEY,
        )
        print(f"SmartArchitect initialized with {FLOOR_PLAN_DETECTOR} detector.")

    def encode_image(self, cv2_img):
        """Convert OpenCV image to base64."""
        _, buffer = cv2.imencode('.jpg', cv2_img)
        return base64.b64encode(buffer).decode('utf-8')

    def identify_room_type(self, room_crop):
        """Identify a room using the configured OpenRouter vision role."""
        base64_image = self.encode_image(room_crop)

        prompt = """Analyze this floor plan room crop. Identify the room type based on the labels, furniture, and fixtures visible.

Choose ONE from this exact list:
- Bedroom (including Master Bedroom, Guest Room, Kids Room)
- Living Room (including Family Room, Salon, Majlis)
- Kitchen
- Bathroom (full bath with shower/tub)
- WC (toilet only, half bath, powder room)
- Dining Room
- Corridor (hallway)
- Closet
- Laundry
- Unknown

- Laundry
- Unknown

If the room combines two functions (e.g., Open Kitchen and Living), choose 'Living Room'.
Output ONLY the room type name, nothing else."""

        try:
            result = self.ai_provider.complete_text(
                role="vision",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=128,
                temperature=0,
                extra_body={
                    "reasoning": {"effort": "minimal", "exclude": True},
                },
            ).strip()
        except Exception as error:
            print(f"    Vision role failed: {type(error).__name__}")
            return "Unknown"

        if not result or len(result) > 50 or "error" in result.lower():
            print("    Vision role returned an invalid room label")
            return "Unknown"
        return result

    def analyze(self, image_path: str, task_id: str = "unknown"):
        """
        Full analysis pipeline with CAD Compliance RAG integration.
        """
        print(f"Analyzing: {image_path}")
        with prepare_floor_plan(image_path) as prepared:
            return self._analyze_image(
                image=prepared.image,
                inference_path=prepared.inference_path,
                task_id=task_id,
            )

    def _analyze_image(self, *, image, inference_path: str, task_id: str):
        img = image
        H, W = img.shape[:2]
        visual_result = img.copy()
        
        # Step 1: Detect geometry locally or through the explicitly selected provider.
        print("1. Detecting walls, openings, and room regions...")
        try:
            detections = self.detector.detect(img, inference_path=inference_path)
        except FloorPlanDetectorError as error:
            print(f"Floor-plan detection failed: {error.code}")
            raise AnalysisPipelineError(error.code) from error

        structure_predictions = detections.structure_predictions()
        room_predictions = detections.room_predictions()
        if not room_predictions:
            raise AnalysisPipelineError("room_detection_empty")
        
        # Step 2: Calculate dynamic scale
        pixels_per_meter = calculate_dynamic_scale(structure_predictions, PIXELS_PER_METER)
        
        # Collect windows
        windows = []
        for item in structure_predictions:
            if "window" in item['class'].lower():
                windows.append(item)
        print(f"Found {len(windows)} windows in the floor plan.")
        
        rooms_data = []
        rooms_for_rag = []  # Format for cad_compliance_rag
        
        # Step 4: Process each room
        print("3. Analyzing rooms with Grok 3 Vision...")
        for i, room in enumerate(room_predictions):
            rx, ry, rw, rh = room['x'], room['y'], room['width'], room['height']
            x1, y1 = int(rx - rw/2), int(ry - rh/2)
            x2, y2 = int(rx + rw/2), int(ry + rh/2)
            
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(W, x2), min(H, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # Crop room for AI identification
            room_crop = img[y1:y2, x1:x2]
            print(f"   - Analyzing room {i+1}...")
            raw_room_type = self.identify_room_type(room_crop)
            normalized_type = normalize_room_type(raw_room_type)
            
            # Window detection with padding
            has_window = False
            search_x1 = x1 - WINDOW_PADDING
            search_y1 = y1 - WINDOW_PADDING
            search_x2 = x2 + WINDOW_PADDING
            search_y2 = y2 + WINDOW_PADDING
            
            for win in windows:
                wx, wy = win['x'], win['y']
                if search_x1 < wx < search_x2 and search_y1 < wy < search_y2:
                    has_window = True
                    break
            
            # Calculate dimensions
            real_w = round(rw / pixels_per_meter, 2)
            real_h = round(rh / pixels_per_meter, 2)
            area_m2 = round(real_w * real_h, 2)
            min_dim_m = round(min(real_w, real_h), 2)
            
            # Build room data for frontend
            room_data = {
                "id": f"room_{i+1}",
                "type": raw_room_type,  # Original for display
                "normalizedType": normalized_type,  # For RAG
                "metrics": {
                    "area": area_m2,
                    "minDim": min_dim_m,
                    "width": real_w,
                    "height": real_h
                },
                "ventilation": {
                    "hasWindow": has_window
                },
                "box": {
                    "x": round(x1 / W, 4),
                    "y": round(y1 / H, 4),
                    "w": round((x2 - x1) / W, 4),
                    "h": round((y2 - y1) / H, 4)
                },
                "polygon": room.get("polygon", []),
                "geometryId": room.get("id", f"room-{i+1}"),
            }
            rooms_data.append(room_data)
            
            # Build room for CAD Compliance RAG
            rooms_for_rag.append({
                "id": i + 1,
                "type": normalized_type,
                "metrics": {
                    "area_sqm": area_m2,
                    "min_dimension_m": min_dim_m
                },
                "ventilation": {
                    "has_window": has_window
                }
            })
        
        # Step 5: Run CAD Compliance RAG
        print("4. Running CAD Compliance RAG analysis...")
        try:
            compliance_result = analyze_plan(
                project_id=task_id,
                asset_id="unit_01",
                rooms=rooms_for_rag
            )
            print(f"Compliance check complete: {compliance_result['summary']['violations_total']} violations")
        except Exception as e:
            print(f"CAD Compliance RAG error: {e}")
            raise AnalysisPipelineError("compliance_failed") from e
        
        # Step 6: Merge compliance results into room data
        violation_room_ids = {v.get("room_id") for v in compliance_result.get("violations", [])}
        
        for room in rooms_data:
            room_num = int(room["id"].split("_")[1])
            room["isCompliant"] = room_num not in violation_room_ids
            
            # Find violation details for this room
            for v in compliance_result.get("violations", []):
                if v.get("room_id") == room_num:
                    room["violation"] = {
                        "rule_id": v.get("rule_id"),
                        "message": v.get("message"),
                        "expected": v.get("expected"),
                        "actual": v.get("actual"),
                        "rule_sentence": v.get("rule_sentence"),
                        "ref": v.get("ref")
                    }
                    
                    # Calculate proposed fix if violation found (Auto-Correction)
                    fix = calculate_proposed_fix(
                        room["box"], 
                        v.get("rule_id"), 
                        v.get("expected"), 
                        room["metrics"], 
                        pixels_per_meter
                    )
                    if fix:
                        room["proposedFix"] = fix
                    break
        
        # Step 7: Draw bounding boxes
        for room in rooms_data:
            box = room["box"]
            x1 = int(box["x"] * W)
            y1 = int(box["y"] * H)
            x2 = int((box["x"] + box["w"]) * W)
            y2 = int((box["y"] + box["h"]) * H)
            
            is_compliant = room.get("isCompliant", True)
            color = (0, 255, 0) if is_compliant else (0, 0, 255)
            cv2.rectangle(visual_result, (x1, y1), (x2, y2), color, 3)
            
            # Draw label
            label = f"{room['type']} | {room['metrics']['area']}m²"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 2
            (label_w, label_h), _ = cv2.getTextSize(label, font, font_scale, thickness)
            cv2.rectangle(visual_result, (x1, y1 - label_h - 10), (x1 + label_w + 10, y1), color, -1)
            cv2.putText(visual_result, label, (x1 + 5, y1 - 5), font, font_scale, (255, 255, 255), thickness)
        
        # Draw structures (doors, windows) in blue
        for item in structure_predictions:
            sx1 = int(item['x'] - item['width'] / 2)
            sy1 = int(item['y'] - item['height'] / 2)
            sx2 = int(item['x'] + item['width'] / 2)
            sy2 = int(item['y'] + item['height'] / 2)
            cv2.rectangle(visual_result, (sx1, sy1), (sx2, sy2), (255, 128, 0), 2)
        
        # Calculate overall score
        total_rooms = len(rooms_data)
        compliant_rooms = sum(1 for r in rooms_data if r.get('isCompliant', True))
        score = round((compliant_rooms / total_rooms * 100) if total_rooms > 0 else 0)
        
        result = {
            "rooms": rooms_data,
            "geometry": {
                "provider": detections.provider,
                "inference_seconds": detections.inference_seconds,
                "walls": [
                    [list(point) for point in polygon]
                    for polygon in detections.wall_polygons
                ],
                "doors": [
                    {
                        "id": opening.id,
                        "box": {
                            "x": opening.box.x,
                            "y": opening.box.y,
                            "width": opening.box.width,
                            "height": opening.box.height,
                        },
                        "polygon": [list(point) for point in opening.polygon],
                    }
                    for opening in detections.doors
                ],
                "windows": [
                    {
                        "id": opening.id,
                        "box": {
                            "x": opening.box.x,
                            "y": opening.box.y,
                            "width": opening.box.width,
                            "height": opening.box.height,
                        },
                        "polygon": [list(point) for point in opening.polygon],
                    }
                    for opening in detections.windows
                ],
            },
            "score": score,
            "status": "Compliant" if score == 100 else "Non-Compliant",
            "total_rooms": total_rooms,
            "compliant_rooms": compliant_rooms,
            "violations_count": compliance_result["summary"]["violations_total"],
            "warnings_count": compliance_result["summary"]["warnings_total"],
            "compliance_details": compliance_result,
            "scale_used": pixels_per_meter,
            "image_width": W,
            "image_height": H
        }
        
        print(f"Analysis complete: {compliant_rooms}/{total_rooms} rooms compliant ({score}%)")
        return result, visual_result
