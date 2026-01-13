# src/rule_engine.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .rules_registry import ROOM_TYPES, build_rules


def _get_area(room: Dict[str, Any]) -> Optional[float]:
    area = None
    metrics = room.get("metrics") or {}
    if isinstance(metrics, dict):
        area = metrics.get("area_sqm")

    if area is None:
        area = room.get("area_m2") or room.get("area_sqm")

    try:
        return float(area) if area is not None else None
    except Exception:
        return None


def _get_min_dim(room: Dict[str, Any]) -> Optional[float]:
    dim = None
    metrics = room.get("metrics") or {}
    if isinstance(metrics, dict):
        dim = metrics.get("min_dimension_m")

    if dim is None:
        dim = room.get("min_dimension_m")

    try:
        return float(dim) if dim is not None else None
    except Exception:
        return None


def _get_has_window(room: Dict[str, Any]) -> Optional[bool]:
    vent = room.get("ventilation") or {}
    if isinstance(vent, dict) and "has_window" in vent:
        return bool(vent.get("has_window"))

    if "has_window" in room:
        return bool(room.get("has_window"))

    return None


def _normalize_type(t: str) -> str:
    t = t or "Unknown"
    return t if t in ROOM_TYPES else "Unknown"


def evaluate_rooms(rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
    rules = build_rules()
    violations: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    skipped_missing_data: List[Dict[str, Any]] = []

    for room in rooms or []:
        room_id = room.get("id")
        rtype = _normalize_type(room.get("type") or "Unknown")

        for rule in rules:
            if rtype not in rule.applies_to:
                continue

            if rule.check == "unknown_type":
                warnings.append({
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "room_id": room_id,
                    "room_type": rtype,
                    "message": "نوع الغرفة غير معروف؛ يلزم تأكيد المستخدم قبل التحقق من الاشتراطات",
                    "expected": None,
                    "actual": None,
                    "evidence_query": rule.evidence_query,
                })
                continue

            if rule.check == "min_area":
                area = _get_area(room)
                if area is None:
                    skipped_missing_data.append({
                        "rule_id": rule.id,
                        "room_id": room_id,
                        "room_type": rtype,
                        "missing": "metrics.area_sqm",
                    })
                    continue

                if area < float(rule.threshold or 0):
                    violations.append({
                        "rule_id": rule.id,
                        "severity": rule.severity,
                        "room_id": room_id,
                        "room_type": rtype,
                        "message": "مساحة الغرفة أقل من الحد الأدنى المطلوب",
                        "expected": f"area_sqm >= {rule.threshold}",
                        "actual": f"area_sqm = {area}",
                        "evidence_query": rule.evidence_query,
                    })
                continue

            if rule.check == "min_width":
                dim = _get_min_dim(room)
                if dim is None:
                    skipped_missing_data.append({
                        "rule_id": rule.id,
                        "room_id": room_id,
                        "room_type": rtype,
                        "missing": "metrics.min_dimension_m",
                    })
                    continue

                if dim < float(rule.threshold or 0):
                    violations.append({
                        "rule_id": rule.id,
                        "severity": rule.severity,
                        "room_id": room_id,
                        "room_type": rtype,
                        "message": "البعد/العرض الأدنى أقل من الحد المطلوب",
                        "expected": f"min_dimension_m >= {rule.threshold}",
                        "actual": f"min_dimension_m = {dim}",
                        "evidence_query": rule.evidence_query,
                    })
                continue

            if rule.check == "has_window":
                has_window = _get_has_window(room)
                if has_window is None:
                    skipped_missing_data.append({
                        "rule_id": rule.id,
                        "room_id": room_id,
                        "room_type": rtype,
                        "missing": "ventilation.has_window",
                    })
                    continue

                if has_window is False:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": rule.severity,
                        "room_id": room_id,
                        "room_type": rtype,
                        "message": "يجب توفر نافذة لدورة المياه/المرحاض",
                        "expected": "has_window = True",
                        "actual": "has_window = False",
                        "evidence_query": rule.evidence_query,
                    })
                continue

    type_counts: Dict[str, int] = {}
    for r in rooms or []:
        t = _normalize_type(r.get("type") or "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    for rule in rules:
        if rule.check != "unit_min_count":
            continue
        if "__UNIT__" not in rule.applies_to:
            continue

        count_types = rule.count_types or []
        required = int(rule.threshold or 1)

        if not count_types:
            warnings.append({
                "rule_id": rule.id,
                "severity": "warning",
                "room_id": None,
                "room_type": "__UNIT__",
                "message": "قاعدة مستوى الوحدة ينقصها إعداد count_types",
                "expected": None,
                "actual": None,
                "evidence_query": rule.evidence_query,
            })
            continue

        actual_count = sum(type_counts.get(t, 0) for t in count_types)

        if actual_count < required:
            violations.append({
                "rule_id": rule.id,
                "severity": rule.severity,
                "room_id": None,
                "room_type": "__UNIT__",
                "message": "الوحدة السكنية ينقصها عنصر مطلوب",
                "expected": f"count({count_types}) >= {required}",
                "actual": f"count({count_types}) = {actual_count}",
                "evidence_query": dict(rule.evidence_query or {}, **{"count_types": count_types}),
            })

    return {
        "summary": {
            "rooms_total": len(rooms or []),
            "violations_total": len(violations),
            "warnings_total": len(warnings),
            "skipped_missing_data": len(skipped_missing_data),
        },
        "violations": violations,
        "warnings": warnings,
        "skipped": skipped_missing_data,
    }
