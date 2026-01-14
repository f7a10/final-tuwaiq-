import ezdxf
from ezdxf.enums import TextEntityAlignment
from typing import List, Dict, Any, Optional


class DxfService:
    """
    DXF file generation service with zone-based intelligent placement.
    """
    
    # Zone definitions for smart placement
    PUBLIC_ZONE = ["Majlis", "Living Room", "Dining Room", "Kitchen", "Entrance"]
    PRIVATE_ZONE = ["Bedroom", "Bathroom"]
    
    # Arabic names for room types
    ROOM_NAMES_AR = {
        "Bedroom": "غرفة نوم",
        "Kitchen": "مطبخ",
        "Bathroom": "دورة مياه",
        "Living Room": "غرفة معيشة",
        "Majlis": "مجلس",
        "Dining Room": "غرفة طعام",
        "Corridor": "ممر",
        "Entrance": "مدخل",
    }
    def generate_dxf(self, rooms_data: List[Dict[str, Any]], output_path: str, use_fixes: bool = False) -> str:
        """
        Generate a DXF file from analyzed room data.
        Auto-calculates the physical scale from room metrics.
        
        Args:
            rooms_data: List of analyzed room objects
            output_path: Path to save the DXF
            use_fixes: If True, uses the 'proposedFix' layout instead of original
        """
        doc = ezdxf.new()
        msp = doc.modelspace()
        
        # Setup Layers
        doc.layers.new(name='WALLS', dxfattribs={'color': 7}) # White/Black
        doc.layers.new(name='ROOM_LABELS', dxfattribs={'color': 3}) # Green
        doc.layers.new(name='DIMENSIONS', dxfattribs={'color': 1}) # Red
        doc.layers.new(name='COMPLIANCE_STATUS', dxfattribs={'color': 6}) # Magenta
        doc.layers.new(name='PROPOSED_FIX', dxfattribs={'color': 4}) # Cyan
        
        # 1. Estimate Canvas Physical Dimensions (Meters)
        widths_estimates = []
        heights_estimates = []
        
        for r in rooms_data:
            m = r.get('metrics', {})
            b = r.get('box', {})
            if m.get('width') and b.get('w') and b.get('w') > 0:
                 widths_estimates.append(m['width'] / b['w'])
            if m.get('height') and b.get('h') and b.get('h') > 0:
                 heights_estimates.append(m['height'] / b['h'])
        
        if not widths_estimates:
            img_width_m = 100.0
            img_height_m = 100.0
        else:
            img_width_m = sum(widths_estimates) / len(widths_estimates)
            img_height_m = sum(heights_estimates) / len(heights_estimates)
            
        print(f"📐 DXF Generation: Estimated Canvas Size: {img_width_m:.2f}m x {img_height_m:.2f}m")

        # 2. Draw Entities
        for room in rooms_data:
            # Determine which geometry to use
            box = room.get('box', {})
            is_fixed = False
            
            if use_fixes and room.get('proposedFix'):
                fix_box = room['proposedFix'].get('box')
                if fix_box:
                    box = fix_box
                    is_fixed = True
            
            rx, ry = box.get('x', 0), box.get('y', 0)
            rw, rh = box.get('w', 0), box.get('h', 0)
            
            # Convert to Meters
            w_m = rw * img_width_m
            h_m = rh * img_height_m
            
            # Calculate Bottom-Left corner in CAD Coordinates
            x_bl = rx * img_width_m
            y_bl = img_height_m - ((ry + rh) * img_height_m)
            
            # Select Layer
            layer = 'PROPOSED_FIX' if is_fixed else 'WALLS'
            
            # Draw Rect (Polyline)
            points = [
                (x_bl, y_bl),
                (x_bl + w_m, y_bl),
                (x_bl + w_m, y_bl + h_m),
                (x_bl, y_bl + h_m),
                (x_bl, y_bl) # Close
            ]
            
            msp.add_lwpolyline(points, dxfattribs={'layer': layer})
            
            # Add Room Label
            room_type = room.get('type', 'Unknown')
            area = room.get('metrics', {}).get('area', 0)
            
            if is_fixed:
                # Recalculate area for label if fixed
                area = round(w_m * h_m, 2)
                label = f"{room_type}\n{area}m2 (FIXED)"
            else:
                label = f"{room_type}\n{area}m2"
            
            # Center of room
            cx = x_bl + w_m/2
            cy = y_bl + h_m/2
            
            # Add text
            # Use set_placement for modern ezdxf versions
            text_entity = msp.add_text(label, dxfattribs={
                'layer': 'ROOM_LABELS', 
                'height': 0.25
            })
            text_entity.set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)
            
            # Add Compliance Status Text if not compliant and not using fix
            if not room.get('isCompliant', True) and not is_fixed:
                violation = room.get('violation', {}).get('message', 'Violation')
                violation_text = msp.add_text(f"X {violation}", dxfattribs={
                    'layer': 'COMPLIANCE_STATUS', 
                    'height': 0.15
                })
                violation_text.set_placement((cx, cy - 0.4), align=TextEntityAlignment.MIDDLE_CENTER)

        doc.saveas(output_path)
        return output_path

    def generate_custom_dxf(self, room_specs: List[Dict[str, Any]], output_path: str, 
                            validation_results: List[Dict] = None) -> str:
        """
        Generate a professional architectural floor plan from room specifications.
        Uses AI-generated placements if available, otherwise falls back to zone-based.
        
        Format: [{ "type": "Bedroom", "width": 4.0, "length": 5.0, "placement": {"x": 0, "y": 0} }, ...]
        """
        doc = ezdxf.new('R2010')  # Use newer DXF version for better compatibility
        msp = doc.modelspace()
        
        # Setup professional layers
        doc.layers.new(name='WALLS', dxfattribs={'color': 7, 'lineweight': 50})  # Thick walls
        doc.layers.new(name='WALLS_INNER', dxfattribs={'color': 8, 'lineweight': 25})  # Inner walls
        doc.layers.new(name='ROOM_LABELS', dxfattribs={'color': 3})  # Green labels
        doc.layers.new(name='DIMENSIONS', dxfattribs={'color': 1})  # Red dimensions
        doc.layers.new(name='DOORS', dxfattribs={'color': 6})  # Door openings
        doc.layers.new(name='TITLE_BLOCK', dxfattribs={'color': 5})  # Title info
        doc.layers.new(name='BOUNDARY', dxfattribs={'color': 4, 'lineweight': 70})  # Outer boundary
        
        wall_thickness = 0.2  # 20cm walls
        
        # Track all room boundaries for outer wall
        all_points = []
        room_rectangles = []
        
        # Check if rooms have AI-generated placements
        has_placements = all('placement' in room for room in room_specs)
        
        if has_placements:
            # Use AI-generated placements
            for i, room in enumerate(room_specs):
                placement = room.get('placement', {})
                x = float(placement.get('x', 0))
                y = float(placement.get('y', 0))
                w = float(room.get('width', placement.get('width', 3)))
                h = float(room.get('length', placement.get('height', 4)))
                rtype = room.get('type', 'Room')
                validation = validation_results[i] if validation_results and i < len(validation_results) else None
                
                room_rectangles.append({
                    'x': x, 'y': y, 'w': w, 'h': h, 
                    'type': rtype, 'validation': validation
                })
                all_points.extend([(x, y), (x+w, y), (x+w, y+h), (x, y+h)])
        else:
            # Fallback to zone-based placement
            current_x, current_y, row_max_h = 0.0, 0.0, 0.0
            max_row_width = 15.0
            
            for i, room in enumerate(room_specs):
                w = float(room.get('width', 3))
                h = float(room.get('length', 4))
                rtype = room.get('type', 'Room')
                validation = validation_results[i] if validation_results and i < len(validation_results) else None
                
                if current_x + w > max_row_width:
                    current_x = 0.0
                    current_y += row_max_h + wall_thickness
                    row_max_h = 0.0
                
                room_rectangles.append({
                    'x': current_x, 'y': current_y, 'w': w, 'h': h,
                    'type': rtype, 'validation': validation
                })
                all_points.extend([(current_x, current_y), (current_x+w, current_y), 
                                   (current_x+w, current_y+h), (current_x, current_y+h)])
                
                current_x += w + wall_thickness
                row_max_h = max(row_max_h, h)
        
        # Calculate bounding box for outer wall
        if all_points:
            min_x = min(p[0] for p in all_points) - wall_thickness
            max_x = max(p[0] for p in all_points) + wall_thickness
            min_y = min(p[1] for p in all_points) - wall_thickness
            max_y = max(p[1] for p in all_points) + wall_thickness
            
            # Draw outer boundary (thick wall)
            outer_points = [
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y),
                (min_x, min_y)
            ]
            msp.add_lwpolyline(outer_points, dxfattribs={'layer': 'BOUNDARY', 'const_width': 0.3})
        
        # Draw each room
        for rect in room_rectangles:
            x, y, w, h = rect['x'], rect['y'], rect['w'], rect['h']
            rtype = rect['type']
            validation = rect.get('validation')
            
            # Draw room walls
            room_points = [
                (x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)
            ]
            msp.add_lwpolyline(room_points, dxfattribs={'layer': 'WALLS_INNER', 'const_width': 0.1})
            
            # Add door opening (1m wide on one wall)
            door_width = 0.9
            door_y = y + h / 2 - door_width / 2
            # Draw door arc
            msp.add_arc(
                center=(x, door_y + door_width),
                radius=door_width,
                start_angle=270,
                end_angle=360,
                dxfattribs={'layer': 'DOORS'}
            )
            
            # Room label
            ar_name = self.ROOM_NAMES_AR.get(rtype, rtype)
            area = round(w * h, 1)
            label = f"{ar_name}\n{w}x{h}m\n{area}m2"
            
            cx, cy = x + w / 2, y + h / 2
            
            text_entity = msp.add_text(label, dxfattribs={
                'layer': 'ROOM_LABELS',
                'height': 0.3
            })
            text_entity.set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)
            
            # Compliance marker
            if validation:
                marker = "[OK]" if validation.get('valid', True) else "[!]"
                color = 3 if validation.get('valid', True) else 1  # Green or Red
                marker_text = msp.add_text(marker, dxfattribs={
                    'layer': 'ROOM_LABELS',
                    'height': 0.2,
                    'color': color
                })
                marker_text.set_placement((cx, y + 0.4), align=TextEntityAlignment.MIDDLE_CENTER)
        
        # Add title block
        if all_points:
            total_area = sum(r['w'] * r['h'] for r in room_rectangles)
            title_y = min_y - 2
            
            title = msp.add_text("EMAD - Generated Floor Plan", dxfattribs={
                'layer': 'TITLE_BLOCK',
                'height': 0.5
            })
            title.set_placement((min_x, title_y), align=TextEntityAlignment.LEFT)
            
            info = msp.add_text(f"Rooms: {len(room_rectangles)} | Total Area: {total_area:.1f}m2", dxfattribs={
                'layer': 'TITLE_BLOCK',
                'height': 0.3
            })
            info.set_placement((min_x, title_y - 0.7), align=TextEntityAlignment.LEFT)
        
        doc.saveas(output_path)
        print(f"DXF saved: {output_path} with {len(room_rectangles)} rooms")
        return output_path
    
    def _place_zone_rooms(self, msp, rooms: List[Dict], start_x: float, start_y: float, 
                          max_width: float, padding: float, zone_layer: str) -> float:
        """
        Place rooms in a zone using row-based packing.
        Returns the total height used by this zone.
        """
        current_x = start_x
        current_y = start_y
        row_max_h = 0.0
        
        for room in rooms:
            w = room['width']
            l = room['length']
            rtype = room['type']
            validation = room.get('validation')
            
            # Check if we need new row
            if current_x + w > max_width:
                current_x = start_x
                current_y += row_max_h + padding
                row_max_h = 0.0
            
            # Determine compliance layer
            is_valid = validation.get('valid', True) if validation else True
            wall_layer = 'WALLS'
            
            # Draw Room Rectangle
            points = [
                (current_x, current_y),
                (current_x + w, current_y),
                (current_x + w, current_y + l),
                (current_x, current_y + l),
                (current_x, current_y)
            ]
            msp.add_lwpolyline(points, dxfattribs={'layer': wall_layer})
            
            # Add Room Label with Arabic name
            ar_name = self.ROOM_NAMES_AR.get(rtype, rtype)
            area = round(w * l, 1)
            label = f"{ar_name}\n{w}x{l}m\n{area}m2"
            
            cx = current_x + w / 2
            cy = current_y + l / 2
            
            text_entity = msp.add_text(label, dxfattribs={
                'layer': 'ROOM_LABELS',
                'height': 0.25
            })
            text_entity.set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)
            
            # Add compliance indicator if validation available
            if validation:
                if is_valid:
                    indicator = msp.add_text("[OK]", dxfattribs={
                        'layer': 'COMPLIANCE_OK',
                        'height': 0.15
                    })
                else:
                    indicator = msp.add_text("[X]", dxfattribs={
                        'layer': 'COMPLIANCE_FAIL',
                        'height': 0.15
                    })
                indicator.set_placement((cx, cy - l/2 + 0.3), align=TextEntityAlignment.MIDDLE_CENTER)
            
            # Update position
            current_x += w + padding
            row_max_h = max(row_max_h, l)
        
        # Return total height used
        return (current_y - start_y) + row_max_h if rooms else 0.0
