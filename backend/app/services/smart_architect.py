# ==========================================
# SmartArchitect ML Analysis Service
# Updated with user's working model code
# ==========================================

import cv2
import base64
import json
import numpy as np
from openai import OpenAI
from inference_sdk import InferenceHTTPClient

from backend.app.config import ROBOFLOW_API_KEY, OPENROUTER_API_KEY, PROJECT_ROOT

# Import Saudi Building Code compliance checker
import sys
sys.path.insert(0, PROJECT_ROOT)
from sbc_rag_sys.src.rag_query import query_sbc

# Engineering settings
PIXELS_PER_METER = 100.0  # Default scale
WINDOW_PADDING = 25       # Pixels to expand search area for windows


def calculate_dynamic_scale(structure_predictions, default_scale=100.0):
    """Calculate pixels per meter based on detected door widths."""
    doors = []
    for item in structure_predictions:
        # Look for single doors only (standard width)
        if "door" in item['class'].lower() and "double" not in item['class'].lower():
            doors.append(item['width'])  # Door width in pixels
    
    if not doors:
        return default_scale
    
    avg_door_pixel_width = sum(doors) / len(doors)
    # Standard door width is ~0.9m
    new_scale = avg_door_pixel_width / 0.9
    
    print(f"📏 Auto-Calibration: Found {len(doors)} doors. Calculated Scale: {new_scale:.2f} px/m")
    return new_scale


class SmartArchitect:
    """Full analysis class for floor plan processing."""
    
    def __init__(self):
        print("🚀 Initializing SmartArchitect...")
        self.ai = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        self.rf = InferenceHTTPClient(
            api_url="https://detect.roboflow.com",
            api_key=ROBOFLOW_API_KEY
        )
        print("✓ SmartArchitect initialized successfully.")

    def encode_image(self, cv2_img):
        """Convert OpenCV image to base64."""
        _, buffer = cv2.imencode('.jpg', cv2_img)
        return base64.b64encode(buffer).decode('utf-8')

    def identify_room_type(self, room_crop):
        """Identify room type with Open Plan support using Vision models."""
        base64_image = self.encode_image(room_crop)

        # Improved prompt for open plan detection
        prompt = """
        Analyze this floor plan crop. Identify the room type based on furniture.
        Rules:
        1. If it contains BOTH kitchen elements (stove/sink) AND living room elements (sofa/TV), output: "Open Plan Kitchen/Living".
        2. Otherwise, use standard names: "Bedroom", "Bathroom", "Kitchen", "Living Room", "Dining Room", "Majlis".
        3. If empty, output: "Unknown".

        Output ONLY the single category name without explanation.
        """

        # Updated vision models - use free/working models
        vision_models = [
            "google/gemini-2.0-flash-exp:free",      # Free Gemini Flash
            "meta-llama/llama-3.2-11b-vision-instruct:free",  # Free Llama Vision
            "qwen/qwen-2-vl-7b-instruct:free",       # Free Qwen Vision
        ]

        for model_id in vision_models:
            try:
                print(f"    🤖 Trying VLM: {model_id}...")
                response = self.ai.chat.completions.create(
                    model=model_id,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }
                    ],
                    max_tokens=50
                )
                result = response.choices[0].message.content.strip()
                print(f"    ✓ {model_id} Identified: {result}")
                
                # Normalize result
                valid_types = ["Bedroom", "Kitchen", "Bathroom", "Living Room", 
                               "Dining Room", "Majlis", "Open Plan Kitchen/Living"]
                for vt in valid_types:
                    if vt.lower() in result.lower():
                        return vt
                
                return result if len(result) < 30 else "Unknown"
                
            except Exception as e:
                print(f"    ⚠️ {model_id} Error: {e}")
                continue

        print("    ❌ All VLM models failed")
        return "Unknown"

    def analyze(self, image_path: str):
        """
        Full analysis pipeline:
        1. Detect structures (doors, windows)
        2. Detect rooms
        3. Identify room types with LLM
        4. Check window presence
        5. Calculate metrics
        6. Check SBC compliance
        7. Draw bounding boxes
        """
        print(f"📐 Analyzing: {image_path}")
        
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            return {"error": "Could not load image"}, None
        
        H, W = img.shape[:2]
        visual_result = img.copy()
        
        # Step 1: Detect structures (doors, windows)
        print("📡 1. Detecting windows and doors (CubiCasa)...")
        try:
            structure_result = self.rf.infer(image_path, model_id="cubicasa5k-2-qpmsa/6")
            structure_predictions = structure_result.get('predictions', [])
        except Exception as e:
            print(f"⚠️ Structure detection failed: {e}")
            structure_predictions = []
        
        # Step 2: Calculate dynamic scale from doors
        pixels_per_meter = calculate_dynamic_scale(structure_predictions, PIXELS_PER_METER)
        
        # Collect all windows
        windows = []
        for item in structure_predictions:
            if "window" in item['class'].lower():
                windows.append(item)
        print(f"ℹ️ Found {len(windows)} windows in the floor plan.")
        
        # Step 3: Detect rooms
        print("📡 2. Detecting rooms (Room Segmentation)...")
        try:
            room_result = self.rf.infer(image_path, model_id="room-detection-6nzte/1")
            room_predictions = room_result.get('predictions', [])
        except Exception as e:
            print(f"⚠️ Room detection failed: {e}")
            room_predictions = []
        
        if not room_predictions:
            print("⚠️ No room regions detected!")
            return {"error": "No rooms detected"}, img
        
        rooms_data = []
        
        # Step 4: Process each room
        print("🧠 3. Analyzing rooms with AI...")
        for i, room in enumerate(room_predictions):
            rx, ry, rw, rh = room['x'], room['y'], room['width'], room['height']
            x1, y1 = int(rx - rw/2), int(ry - rh/2)
            x2, y2 = int(rx + rw/2), int(ry + rh/2)
            
            # Ensure bounds are within image
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(W, x2), min(H, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # Crop room for AI identification
            room_crop = img[y1:y2, x1:x2]
            print(f"   - Analyzing room {i+1}...")
            room_type = self.identify_room_type(room_crop)
            
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
            
            # Calculate real dimensions
            real_w = round(rw / pixels_per_meter, 2)
            real_h = round(rh / pixels_per_meter, 2)
            area_m2 = round(real_w * real_h, 2)
            min_dim_m = min(real_w, real_h)
            
            # Check SBC compliance
            sbc_result = query_sbc(room_type, area_m2, min_dim_m)
            is_compliant = sbc_result["is_compliant"]
            rag_reason = sbc_result["reason"]
            
            # Additional ventilation check
            needs_window = room_type in ["Bedroom", "Living Room", "Majlis", "Dining Room"]
            if needs_window and not has_window:
                is_compliant = False
                rag_reason = "الغرفة تتطلب نافذة للتهوية الطبيعية حسب كود البناء السعودي"
            
            # Draw bounding box
            color = (0, 255, 0) if is_compliant else (0, 0, 255)  # Green or Red
            cv2.rectangle(visual_result, (x1, y1), (x2, y2), color, 3)
            
            # Draw label
            label = f"{room_type} | {area_m2}m2 (min: {min_dim_m}m)"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 2
            (label_w, label_h), _ = cv2.getTextSize(label, font, font_scale, thickness)
            cv2.rectangle(visual_result, (x1, y1 - label_h - 10), (x1 + label_w + 10, y1), color, -1)
            cv2.putText(visual_result, label, (x1 + 5, y1 - 5), font, font_scale, (255, 255, 255), thickness)
            
            # Store room data
            rooms_data.append({
                "id": f"room_{i+1}",
                "type": room_type,
                "metrics": {
                    "area": area_m2,
                    "minDim": min_dim_m,
                    "width": real_w,
                    "height": real_h
                },
                "ventilation": {
                    "hasWindow": has_window
                },
                "isCompliant": is_compliant,
                "ragReason": rag_reason,
                "box": {
                    "x": round(x1 / W, 4),
                    "y": round(y1 / H, 4),
                    "w": round((x2 - x1) / W, 4),
                    "h": round((y2 - y1) / H, 4)
                }
            })
        
        # Draw detected windows/doors in blue
        for item in structure_predictions:
            sx1 = int(item['x'] - item['width'] / 2)
            sy1 = int(item['y'] - item['height'] / 2)
            sx2 = int(item['x'] + item['width'] / 2)
            sy2 = int(item['y'] + item['height'] / 2)
            cv2.rectangle(visual_result, (sx1, sy1), (sx2, sy2), (255, 128, 0), 2)
        
        # Calculate overall score
        total_rooms = len(rooms_data)
        compliant_rooms = sum(1 for r in rooms_data if r['isCompliant'])
        score = round((compliant_rooms / total_rooms * 100) if total_rooms > 0 else 0)
        
        result = {
            "rooms": rooms_data,
            "score": score,
            "status": "Compliant" if score == 100 else "Non-Compliant",
            "total_rooms": total_rooms,
            "compliant_rooms": compliant_rooms,
            "scale_used": pixels_per_meter
        }
        
        print(f"✅ Analysis complete: {compliant_rooms}/{total_rooms} rooms compliant ({score}%)")
        return result, visual_result
