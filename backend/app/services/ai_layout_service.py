# ==========================================
# AI Layout Service - Intelligent Floor Plan Generation
# ==========================================

import sys
from typing import List, Dict, Any, Optional
from openai import OpenAI

from backend.app.config import OPENROUTER_API_KEY, PROJECT_ROOT

# Ensure cad_compliance_rag is in path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from cad_compliance_rag.src.retrieval import retrieve_evidence
except ImportError as e:
    print(f"Warning: Could not import retrieval module: {e}")
    retrieve_evidence = None


class AILayoutService:
    """
    AI-powered layout planning service that uses RAG to retrieve
    SBC requirements and LLM to generate intelligent room placements.
    """
    
    # SBC Minimum Requirements (fallback if RAG fails)
    DEFAULT_MINIMUMS = {
        "Bedroom": {"min_area": 9.0, "min_dim": 2.5},
        "Kitchen": {"min_area": 4.5, "min_dim": 1.8},
        "Bathroom": {"min_area": 2.5, "min_dim": 1.2},
        "Living Room": {"min_area": 12.0, "min_dim": 3.0},
        "Majlis": {"min_area": 12.0, "min_dim": 3.0},
        "Dining Room": {"min_area": 9.0, "min_dim": 2.5},
        "Corridor": {"min_area": 1.5, "min_dim": 1.0},
        "Entrance": {"min_area": 3.0, "min_dim": 1.5},
    }
    
    # Zone definitions for smart placement
    PUBLIC_ZONE = ["Majlis", "Living Room", "Dining Room", "Kitchen", "Entrance"]
    PRIVATE_ZONE = ["Bedroom", "Bathroom"]
    
    # Adjacency rules (room_type -> preferred neighbors)
    ADJACENCY_RULES = {
        "Kitchen": ["Dining Room", "Living Room"],
        "Dining Room": ["Kitchen", "Living Room", "Majlis"],
        "Bedroom": ["Bathroom", "Corridor"],
        "Bathroom": ["Bedroom", "Corridor"],
        "Majlis": ["Entrance", "Dining Room"],
        "Living Room": ["Dining Room", "Kitchen", "Entrance"],
    }
    
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
    
    def get_room_requirements(self, room_type: str) -> Dict[str, Any]:
        """
        Retrieve SBC requirements for a room type using RAG.
        Falls back to defaults if RAG is unavailable.
        """
        requirements = self.DEFAULT_MINIMUMS.get(room_type, {"min_area": 6.0, "min_dim": 2.0})
        
        if retrieve_evidence:
            try:
                # Query RAG for room requirements
                evidence_query = {
                    "keywords": [room_type, "minimum area", "minimum dimension", "requirements"],
                    "room_type": room_type,
                    "boost_keywords": ["minimum", "area", "dimension", "meter", "square"],
                    "doc": "__ALL__"
                }
                
                results = retrieve_evidence(evidence_query, top_k=3)
                
                if results:
                    # Extract requirements from RAG results
                    # This is a simplified extraction - in production, use NLP
                    for r in results:
                        quote = r.get('quote', '')
                        # Look for area patterns like "9 m2" or "9 square meters"
                        import re
                        area_match = re.search(r'(\d+\.?\d*)\s*(?:m2|متر|square)', quote, re.IGNORECASE)
                        if area_match:
                            requirements['min_area'] = float(area_match.group(1))
                            requirements['source'] = f"{r.get('doc')} - {r.get('section')}"
                            break
                            
            except Exception as e:
                print(f"RAG retrieval failed for {room_type}: {e}")
        
        return requirements
    
    def validate_room(self, room: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single room against SBC requirements.
        Returns validation result with compliance status and recommendations.
        """
        room_type = room.get('type', 'Unknown')
        width = float(room.get('width', 0))
        length = float(room.get('length', 0))
        area = width * length
        min_dim = min(width, length)
        
        # Get requirements from RAG
        requirements = self.get_room_requirements(room_type)
        req_area = requirements.get('min_area', 0)
        req_dim = requirements.get('min_dim', 0)
        source = requirements.get('source', 'SBC 1101')
        
        # Check compliance
        area_valid = area >= req_area
        dim_valid = min_dim >= req_dim
        is_valid = area_valid and dim_valid
        
        # Build response
        result = {
            "valid": is_valid,
            "room_type": room_type,
            "current_area": round(area, 2),
            "current_min_dim": round(min_dim, 2),
            "required_area": req_area,
            "required_min_dim": req_dim,
            "source": source,
            "issues": []
        }
        
        if not area_valid:
            deficit = round(req_area - area, 2)
            result["issues"].append(f"المساحة أقل من الحد الأدنى ({req_area}م²) بمقدار {deficit}م²")
        
        if not dim_valid:
            deficit = round(req_dim - min_dim, 2)
            result["issues"].append(f"أقل بُعد ({min_dim}م) أقل من الحد الأدنى ({req_dim}م)")
        
        if is_valid:
            result["message"] = f"مطابق لمتطلبات الكود [{source}]"
        else:
            result["message"] = " | ".join(result["issues"])
        
        return result
    
    def auto_correct_dimensions(self, room: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically adjust room dimensions to meet SBC minimums.
        """
        room_type = room.get('type', 'Unknown')
        width = float(room.get('width', 3))
        length = float(room.get('length', 4))
        
        requirements = self.get_room_requirements(room_type)
        req_area = requirements.get('min_area', 0)
        req_dim = requirements.get('min_dim', 0)
        
        corrected = room.copy()
        
        # Ensure minimum dimension
        if width < req_dim:
            corrected['width'] = req_dim
            width = req_dim
        if length < req_dim:
            corrected['length'] = req_dim
            length = req_dim
        
        # Ensure minimum area
        current_area = width * length
        if current_area < req_area:
            # Scale up proportionally
            scale = (req_area / current_area) ** 0.5
            corrected['width'] = round(width * scale, 1)
            corrected['length'] = round(length * scale, 1)
        
        corrected['auto_corrected'] = True
        return corrected
    
    def get_smart_correction(self, room_type: str, current_width: float, current_length: float) -> Dict[str, Any]:
        """
        Use LLM + RAG to provide intelligent correction suggestions.
        Analyzes the room and suggests optimal dimensions with explanations.
        """
        import json
        
        # Get SBC requirements via RAG
        requirements = self.get_room_requirements(room_type)
        req_area = requirements.get('min_area', 9.0)
        req_dim = requirements.get('min_dim', 2.5)
        source = requirements.get('source', 'SBC 1101')
        
        current_area = current_width * current_length
        current_min_dim = min(current_width, current_length)
        
        # Check if already compliant
        if current_area >= req_area and current_min_dim >= req_dim:
            return {
                "suggestion": f"الغرفة مطابقة بالفعل لمتطلبات كود البناء السعودي. المساحة الحالية ({current_area:.1f}م²) تتجاوز الحد الأدنى ({req_area}م²).",
                "recommended_width": None,
                "recommended_length": None,
                "is_compliant": True,
                "rag_source": source
            }
        
        # Calculate optimal correction
        # Strategy: Keep aspect ratio similar but meet minimums
        aspect_ratio = current_width / current_length if current_length > 0 else 1.0
        
        # Ensure minimum dimension
        new_width = max(current_width, req_dim)
        new_length = max(current_length, req_dim)
        
        # Check if area is now sufficient
        new_area = new_width * new_length
        if new_area < req_area:
            # Need to increase - scale proportionally
            scale = (req_area / new_area) ** 0.5
            new_width = round(new_width * scale, 1)
            new_length = round(new_length * scale, 1)
        
        # Round to nice numbers (0.5 increments)
        new_width = round(new_width * 2) / 2
        new_length = round(new_length * 2) / 2
        
        # Ensure minimums after rounding
        new_width = max(new_width, req_dim)
        new_length = max(new_length, req_dim)
        
        # Use LLM for intelligent suggestion text
        ar_room_names = {
            "Bedroom": "غرفة النوم",
            "Kitchen": "المطبخ",
            "Bathroom": "دورة المياه",
            "Living Room": "غرفة المعيشة",
            "Majlis": "المجلس",
            "Dining Room": "غرفة الطعام"
        }
        ar_name = ar_room_names.get(room_type, room_type)
        
        prompt = f"""أنت مهندس معماري خبير. قدم نصيحة مختصرة (جملتين فقط) لتعديل غرفة.

نوع الغرفة: {ar_name}
الأبعاد الحالية: {current_width}م × {current_length}م = {current_area:.1f}م²
الحد الأدنى المطلوب: مساحة {req_area}م²، أقل بُعد {req_dim}م
الأبعاد المقترحة: {new_width}م × {new_length}م = {new_width * new_length:.1f}م²

اكتب نصيحة مختصرة بالعربية توضح سبب التعديل وفائدته."""

        suggestion_text = f"لتحقيق متطلبات الكود، يُنصح بزيادة أبعاد {ar_name} إلى {new_width}م × {new_length}م (مساحة {new_width * new_length:.1f}م²). هذا يضمن استيفاء الحد الأدنى للمساحة ({req_area}م²) والبُعد ({req_dim}م)."
        
        try:
            models = ["x-ai/grok-2-1212", "openai/gpt-4o-mini", "google/gemini-flash-1.5"]
            
            for model_id in models:
                try:
                    response = self.client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "أنت مهندس معماري سعودي خبير. قدم نصائح مختصرة ومفيدة."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150,
                        temperature=0.5
                    )
                    
                    ai_suggestion = response.choices[0].message.content.strip()
                    if ai_suggestion and len(ai_suggestion) > 20:
                        suggestion_text = ai_suggestion
                        break
                        
                except Exception as e:
                    print(f"LLM {model_id} failed: {e}")
                    continue
                    
        except Exception as e:
            print(f"LLM suggestion failed, using default: {e}")
        
        return {
            "suggestion": suggestion_text,
            "recommended_width": new_width,
            "recommended_length": new_length,
            "recommended_area": round(new_width * new_length, 1),
            "is_compliant": False,
            "current_issues": {
                "area_deficit": round(req_area - current_area, 1) if current_area < req_area else 0,
                "dim_deficit": round(req_dim - current_min_dim, 1) if current_min_dim < req_dim else 0
            },
            "rag_source": source
        }
    
    def plan_layout(self, rooms: List[Dict[str, Any]], validate: bool = True) -> Dict[str, Any]:
        """
        Plan an intelligent layout for the given rooms using LLM + RAG.
        
        Args:
            rooms: List of room specifications [{"type": "Bedroom", "width": 4, "length": 5}]
            validate: If True, validate and auto-correct dimensions
            
        Returns:
            Optimized layout with placements and validation results
        """
        result = {
            "rooms": [],
            "validation_results": [],
            "layout_suggestions": [],
            "total_area": 0,
            "zones": {"public": [], "private": []},
            "ai_layout": None
        }
        
        # 1. Validate and optionally correct each room
        for room in rooms:
            validation = self.validate_room(room)
            result["validation_results"].append(validation)
            
            if validate and not validation["valid"]:
                corrected = self.auto_correct_dimensions(room)
                result["rooms"].append(corrected)
            else:
                result["rooms"].append(room.copy())
        
        # 2. Categorize rooms into zones
        for i, room in enumerate(result["rooms"]):
            room_type = room.get('type', 'Unknown')
            if room_type in self.PUBLIC_ZONE:
                result["zones"]["public"].append(i)
            else:
                result["zones"]["private"].append(i)
        
        # 3. Calculate total area
        for room in result["rooms"]:
            width = float(room.get('width', 0))
            length = float(room.get('length', 0))
            result["total_area"] += width * length
        
        result["total_area"] = round(result["total_area"], 2)
        
        # 4. Use LLM to generate intelligent layout
        try:
            ai_layout = self._generate_ai_layout(result["rooms"])
            if ai_layout:
                result["ai_layout"] = ai_layout
                result["layout_suggestions"] = ai_layout.get("suggestions", [])
                # Apply AI-generated placements
                placements = ai_layout.get("placements", [])
                if placements and len(placements) == len(result["rooms"]):
                    for i, room in enumerate(result["rooms"]):
                        room["placement"] = placements[i]
                    return result
        except Exception as e:
            print(f"AI layout generation failed: {e}")
        
        # 5. Fallback to rule-based placements
        suggestions = self._generate_layout_suggestions(result["rooms"])
        result["layout_suggestions"] = suggestions
        
        placements = self._calculate_placements(result["rooms"], result["zones"])
        for i, room in enumerate(result["rooms"]):
            room["placement"] = placements[i]
        
        return result
    
    def _generate_ai_layout(self, rooms: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Use LLM to generate an intelligent floor plan layout.
        """
        import json
        
        # Build room description for LLM
        room_list = []
        for i, room in enumerate(rooms):
            room_list.append(f"{i+1}. {room.get('type')}: {room.get('width')}m x {room.get('length')}m")
        
        rooms_text = "\n".join(room_list)
        total_area = sum(r.get('width', 0) * r.get('length', 0) for r in rooms)
        
        # Get RAG context for architectural guidelines
        rag_context = ""
        if retrieve_evidence:
            try:
                evidence_query = {
                    "keywords": ["floor plan", "layout", "room arrangement", "design"],
                    "boost_keywords": ["adjacent", "near", "entrance", "private", "public"],
                    "doc": "__ALL__"
                }
                results = retrieve_evidence(evidence_query, top_k=3)
                if results:
                    rag_context = "\n".join([r.get('quote', '')[:300] for r in results])
            except Exception as e:
                print(f"RAG retrieval for layout failed: {e}")
        
        # Default architectural guidelines if RAG fails
        default_guidelines = (
            "- Public areas (Majlis, Living, Dining, Kitchen) should be near entrance\n"
            "- Private areas (Bedrooms, Bathrooms) should be separated\n"
            "- Kitchen should be adjacent to Dining Room\n"
            "- Bathrooms should be accessible from bedrooms"
        )
        
        guidelines = rag_context if rag_context else default_guidelines
        
        prompt = f"""You are an expert architect designing a Saudi residential floor plan.

Given these rooms:
{rooms_text}

Total area: {total_area:.1f} m²

Architectural Guidelines:
{guidelines}

Generate a professional floor plan layout. Return ONLY a JSON object with this exact structure:
{{
  "placements": [
    {{"x": 0, "y": 0, "width": W, "height": H}},
    ...
  ],
  "suggestions": ["suggestion1", "suggestion2"],
  "layout_type": "L-shape|Rectangle|U-shape",
  "description": "Brief layout description in Arabic"
}}

Rules for placements:
1. All coordinates in meters, starting from (0,0)
2. Rooms should share walls (no gaps except 0.2m for walls)
3. Create a realistic floor plan shape (L-shape, rectangle, etc.)
4. Public zone rooms grouped together near (0,0)
5. Private zone rooms in a separate wing
6. Total width should not exceed 15m

Return ONLY the JSON, no explanation."""

        try:
            models = ["x-ai/grok-2-1212", "openai/gpt-4o-mini", "google/gemini-flash-1.5"]
            
            for model_id in models:
                try:
                    response = self.client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "You are an expert architect. Return only valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=1000,
                        temperature=0.3
                    )
                    
                    content = response.choices[0].message.content.strip()
                    
                    # Extract JSON from response
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    
                    layout = json.loads(content)
                    print(f"AI Layout generated via {model_id}")
                    return layout
                    
                except Exception as e:
                    print(f"Model {model_id} failed: {e}")
                    continue
                    
        except Exception as e:
            print(f"AI layout generation error: {e}")
        
        return None
    
    def _generate_layout_suggestions(self, rooms: List[Dict[str, Any]]) -> List[str]:
        """Generate layout suggestions based on adjacency rules."""
        suggestions = []
        room_types = [r.get('type') for r in rooms]
        
        # Check adjacency recommendations
        for room_type in room_types:
            preferred = self.ADJACENCY_RULES.get(room_type, [])
            for neighbor in preferred:
                if neighbor in room_types and room_type != neighbor:
                    suggestions.append(f"يُفضل وضع {self._ar_name(room_type)} بجوار {self._ar_name(neighbor)}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)
        
        return unique_suggestions[:5]  # Limit to 5 suggestions
    
    def _ar_name(self, room_type: str) -> str:
        """Get Arabic name for room type."""
        names = {
            "Bedroom": "غرفة النوم",
            "Kitchen": "المطبخ",
            "Bathroom": "دورة المياه",
            "Living Room": "غرفة المعيشة",
            "Majlis": "المجلس",
            "Dining Room": "غرفة الطعام",
            "Corridor": "الممر",
            "Entrance": "المدخل",
        }
        return names.get(room_type, room_type)
    
    def _calculate_placements(self, rooms: List[Dict[str, Any]], zones: Dict[str, List[int]]) -> List[Dict[str, float]]:
        """
        Calculate room placements using zone-based algorithm.
        Public rooms on one side, private on the other.
        """
        placements = []
        
        # Layout parameters
        padding = 0.2  # Wall thickness
        max_row_width = 15.0
        
        # Place public zone rooms first (bottom)
        current_x = 0.0
        current_y = 0.0
        row_max_h = 0.0
        
        for i, room in enumerate(rooms):
            width = float(room.get('width', 3))
            length = float(room.get('length', 4))
            
            # Check if we need a new row
            if current_x + width > max_row_width:
                current_x = 0.0
                current_y += row_max_h + padding
                row_max_h = 0.0
            
            placements.append({
                "x": current_x,
                "y": current_y,
                "width": width,
                "height": length
            })
            
            current_x += width + padding
            row_max_h = max(row_max_h, length)
        
        return placements


# Singleton instance
ai_layout_service = AILayoutService()
