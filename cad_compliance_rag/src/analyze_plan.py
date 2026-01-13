# src/analyze_plan.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .rule_engine import evaluate_rooms
from .retrieval import retrieve_evidence
from .text_picker import pick_best_sentence


def _is_table_rule(rule_id: str) -> bool:
    return (rule_id or "").startswith("SBC-TABLE-")


def _make_table_rule_sentence(item: Dict[str, Any]) -> Optional[str]:
    import re

    rid = item.get("rule_id", "")
    room_type = item.get("room_type", "")
    exp = item.get("expected", "")

    m = re.search(r">=\s*([0-9.]+)", exp or "")
    val = m.group(1) if m else None

    if "MIN-AREA" in rid and val:
        return f"لا يقل الحد الأدنى لمساحة {room_type} عن {val} م²."
    if "MIN-WIDTH" in rid and val:
        return f"لا يقل الحد الأدنى للعرض/البعد الأدنى لـ {room_type} عن {val} م."
    return None


def _format_for_reading(result: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "project_id": result.get("project_id"),
        "asset_id": result.get("asset_id"),
        "summary": result.get("summary"),
        "violations": [],
        "warnings": [],
    }

    for bucket in ("violations", "warnings"):
        for item in result.get(bucket, []):
            ev0 = (item.get("evidence_used") or item.get("evidence") or [{}])[0] or {}
            out[bucket].append({
                "rule_id": item.get("rule_id"),
                "room_id": item.get("room_id"),
                "room_type": item.get("room_type"),
                "expected": item.get("expected"),
                "actual": item.get("actual"),
                "rule_sentence": item.get("rule_sentence"),
                "ref": {
                    "doc": ev0.get("doc"),
                    "section": ev0.get("section"),
                    "page": ev0.get("page"),
                    "chunk_id": ev0.get("chunk_id"),
                    "source": ev0.get("source"),
                }
            })
    return out


def analyze_plan(
    *,
    project_id: str,
    asset_id: str,
    rooms: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    rooms = rooms or []
    result = evaluate_rooms(rooms)

    for bucket in ("violations", "warnings"):
        for item in result.get(bucket, []):
            eq = item.get("evidence_query") or {}
            if not eq:
                continue

            prefer: List[str] = []

            # Narrow evidence search for specific rule IDs when needed.
            if item.get("rule_id") == "SBC-UNIT-MIN-1-KITCHEN":
                eq = dict(eq)
                eq["must_include_any_keywords"] = ["مطبخ", "بمطبخ", "بالمطبخ", "مطابخ"]
                prefer = ["مطبخ", "بمطبخ", "حوض", "غسيل"]

            elif item.get("rule_id") == "SBC-UNIT-MIN-1-EXIT-DOOR":
                prefer = ["باب", "خروج", "وحدة سكنية"]

            evidence = retrieve_evidence(eq, top_k=3)
            item["evidence"] = evidence

            # Table rules use a deterministic sentence.
            if _is_table_rule(item.get("rule_id", "")):
                item["rule_sentence"] = _make_table_rule_sentence(item)
                item["evidence_used"] = evidence[:1]
                continue

            # Pick one short sentence from the top evidence chunk.
            if evidence:
                best = evidence[0]
                sentence = pick_best_sentence(best.get("quote", ""), prefer=prefer)
                item["rule_sentence"] = sentence
                item["evidence_used"] = [best]

    final = {"project_id": project_id, "asset_id": asset_id, **result}
    return _format_for_reading(final)
