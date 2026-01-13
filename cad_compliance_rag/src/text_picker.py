# src/text_picker.py
import re
from typing import List, Optional

AR_SENTENCE_SPLIT = r"[.\n؟!؛]+"


def pick_best_sentence(text: str, prefer: List[str]) -> Optional[str]:
    """
    Pick one short sentence that is likely to express a requirement:
    - Contains obligation terms (e.g., يجب / لا يجوز / يلزم / يشترط)
    - Boosted by preferred keywords when provided
    """
    if not text:
        return None

    sentences = [
        s.strip()
        for s in re.split(AR_SENTENCE_SPLIT, text)
        if len(s.strip()) > 10
    ]

    scored = []
    for s in sentences:
        score = 0

        if any(k in s for k in ["يجب", "لا يجوز", "يلزم", "يشترط"]):
            score += 3

        for kw in prefer:
            if kw in s:
                score += 2

        if score > 0:
            scored.append((score, s))

    if not scored:
        return None

    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[0][1]
