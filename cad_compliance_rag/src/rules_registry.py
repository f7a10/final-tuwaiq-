# src/rules_registry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


ROOM_TYPES = {
    "Living",
    "Bedroom",
    "Kitchen",
    "Bathroom",
    "WC",
    "Corridor",
    "ServiceRoom",
    "ExitDoor",
    "Unknown",
}

TABLE_LIMITS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    "Living": (11.2, 2.8),
    "Bedroom": (6.5, 2.1),
    "Kitchen": (5.0, 1.8),
    "Bathroom": (2.8, 1.4),
    "WC": (1.5, 1.0),
    "ServiceRoom": (6.5, 2.1),
    "Corridor": (None, 0.9),
}


@dataclass
class Rule:
    id: str
    title: str
    severity: str
    applies_to: List[str]
    check: str
    threshold: Optional[float] = None
    count_types: Optional[List[str]] = None
    evidence_query: Optional[Dict[str, Any]] = None


def build_rules() -> List[Rule]:
    rules: List[Rule] = []

    for rtype, (min_area, min_width) in TABLE_LIMITS.items():
        if min_area is not None:
            rules.append(
                Rule(
                    id=f"SBC-TABLE-{rtype}-MIN-AREA",
                    title=f"Minimum area for {rtype}",
                    severity="violation",
                    applies_to=[rtype],
                    check="min_area",
                    threshold=min_area,
                    evidence_query={
                        "doc": "اشتراطات إنشاء المباني السكنية",
                        "section_hint": "مساحات الغرف والفراغات السكنية",
                        "room_type": rtype,
                        "metric": "area",
                    },
                )
            )

        if min_width is not None:
            rules.append(
                Rule(
                    id=f"SBC-TABLE-{rtype}-MIN-WIDTH",
                    title=f"Minimum width for {rtype}",
                    severity="violation",
                    applies_to=[rtype],
                    check="min_width",
                    threshold=min_width,
                    evidence_query={
                        "doc": "اشتراطات إنشاء المباني السكنية",
                        "section_hint": "مساحات الغرف والفراغات السكنية",
                        "room_type": rtype,
                        "metric": "width",
                    },
                )
            )

    rules.append(
        Rule(
            id="SBC1101-HABITABLE-HAS-WINDOW",
            title="Habitable rooms must have natural light/ventilation (Window)",
            severity="violation",
            applies_to=["Bedroom", "Living", "Kitchen"],
            check="has_window",
            evidence_query={
                "doc": "SBC1101",
                "section_hint": "التهوية والإضاءة",
                "keywords": ["تهوية طبيعية", "نوافذ", "مساحة زجاجية", "غرف نوم", "معيشة"],
            },
        )
    )

    rules.append(
        Rule(
            id="SBC1101-BATH-WC-HAS-WINDOW",
            title="Bathrooms/WC must have ventilation (Window/Fan)",
            severity="warning", # Downgraded to warning as mechanical vent is allowed
            applies_to=["Bathroom", "WC"],
            check="has_window",
            evidence_query={
                "doc": "SBC1101",
                "section_hint": "دورات المياه",
                "keywords": ["الحمامات", "دورات المياه", "نوافذ", "مروحة شفط"],
            },
        )
    )

    rules.append(
        Rule(
            id="SBC-UNIT-MIN-1-KITCHEN",
            title="Each dwelling unit must include a kitchen",
            severity="violation",
            applies_to=["__UNIT__"],
            check="unit_min_count",
            threshold=1,
            count_types=["Kitchen"],
            evidence_query={
                "doc": "SBC1101",
                "section_hint": "الصرف الصحي",
                "keywords": ["وحدة سكنية", "مطبخ", "حوض", "غسيل"],
                "must_include_any_keywords": ["مطبخ", "بمطبخ", "بالمطبخ", "مطابخ"],
                "boost_keywords": ["حوض", "غسيل"],
                "exclude_hints": ["التعاريف", "تعريف", "Definitions"],
            },
        )
    )

    rules.append(
        Rule(
            id="SBC-UNIT-MIN-1-BATHROOM",
            title="Each dwelling unit must include at least one bathroom/WC",
            severity="violation",
            applies_to=["__UNIT__"],
            check="unit_min_count",
            threshold=1,
            count_types=["Bathroom", "WC"],
            evidence_query={
                "doc": "SBC1101",
                "section_hint": "الصرف الصحي",
                "keywords": ["وحدة سكنية", "دورة مياه", "مرحاض"],
                "must_include_any_keywords": ["دورة", "مياه", "مرحاض", "مراحيض"],
                "exclude_hints": ["التعاريف", "تعريف", "Definitions"],
            },
        )
    )

    rules.append(
        Rule(
            id="SBC-UNIT-MIN-1-EXIT-DOOR",
            title="Each dwelling unit must have at least one exit door",
            severity="violation",
            applies_to=["__UNIT__"],
            check="unit_min_count",
            threshold=1,
            count_types=["ExitDoor"],
            evidence_query={
                "doc": "SBC1101",
                "section_hint": "وسائل الخروج",
                "keywords": ["باب خروج", "وسائل الخروج", "وحدة سكنية", "واحد على الأقل"],
                "must_include_any_keywords": ["باب", "خروج"],
            },
        )
    )

    rules.append(
        Rule(
            id="ROOM-TYPE-UNKNOWN",
            title="Room type is Unknown (requires user confirmation)",
            severity="warning",
            applies_to=["Unknown"],
            check="unknown_type",
        )
    )

    return rules
