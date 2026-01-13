# src/retrieval.py
from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Use relative import for config
import sys
import os
_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _pkg_root)
import config


AR_NUM_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def normalize_arabic(text: str) -> str:
    """
    Search normalization:
    - Arabic digits -> Latin digits
    - lowercase
    - collapse spaces
    - unify Arabic letter variants
    - remove diacritics/tatweel
    """
    text = (text or "").translate(AR_NUM_MAP)
    text = re.sub(r"\s+", " ", text).strip().lower()
    text = re.sub("[إأآٱ]", "ا", text)
    text = re.sub("ى", "ي", text)
    text = re.sub("ؤ", "و", text)
    text = re.sub("ئ", "ي", text)
    text = re.sub("ة", "ه", text)
    text = re.sub("[ًٌٍَُِّْـ]", "", text)
    return text


def tokenize(text: str) -> List[str]:
    t = normalize_arabic(text)
    return re.findall(r"[a-z0-9\u0600-\u06ff]+", t)


@lru_cache(maxsize=16)
def _load_chunks(jsonl_path: str) -> List[Dict[str, Any]]:
    p = Path(jsonl_path)
    if not p.exists():
        raise FileNotFoundError(f"Chunks file not found: {jsonl_path}")

    rows: List[Dict[str, Any]] = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _bm25_rank(
    query_tokens: List[str],
    docs_tokens: List[List[str]],
    k1: float = 1.5,
    b: float = 0.75,
) -> List[float]:
    """Lightweight BM25 over token lists (no external deps)."""
    N = len(docs_tokens)
    if N == 0:
        return []

    df: Dict[str, int] = {}
    for dt in docs_tokens:
        for w in set(dt):
            df[w] = df.get(w, 0) + 1

    avgdl = (sum(len(dt) for dt in docs_tokens) / max(1, N)) or 1.0

    def idf(w: str) -> float:
        n = df.get(w, 0)
        return math.log(1 + (N - n + 0.5) / (n + 0.5))

    scores: List[float] = []
    for dt in docs_tokens:
        dl = len(dt) or 1
        tf: Dict[str, int] = {}
        for w in dt:
            tf[w] = tf.get(w, 0) + 1

        s = 0.0
        for w in query_tokens:
            f = tf.get(w, 0)
            if f == 0:
                continue
            denom = f + k1 * (1 - b + b * (dl / avgdl))
            s += idf(w) * (f * (k1 + 1) / denom)

        scores.append(s)

    return scores


def _chunks_paths_by_doc(doc: str) -> List[str]:
    """Resolve doc name -> KB jsonl path(s)."""
    mapping = {
        "SBC1101": config.KB_SBC1101_PATH,
        "اشتراطات إنشاء المباني السكنية": config.KB_RES_REQ_PATH,
        "__ALL__": config.KB_ALL_PATH,
    }
    if doc in mapping:
        return [mapping[doc]]
    return [mapping["__ALL__"]]


def build_query(evidence_query: Dict[str, Any]) -> str:
    """Build a ranking query string from a structured evidence_query."""
    if not evidence_query:
        return ""

    parts: List[str] = []

    if evidence_query.get("section_hint"):
        parts.append(str(evidence_query["section_hint"]))

    if evidence_query.get("keywords"):
        parts.extend([str(k) for k in evidence_query["keywords"] if k])

    if evidence_query.get("room_type"):
        parts.append(str(evidence_query["room_type"]))

    if evidence_query.get("metric"):
        parts.append(str(evidence_query["metric"]))

    if evidence_query.get("doc"):
        parts.append(str(evidence_query["doc"]))

    return " ".join(parts).strip()


def _hard_filter_all_tokens(text: str, must_include_all: List[str]) -> bool:
    if not must_include_all:
        return True

    tokens = set(tokenize(text))
    for kw in must_include_all:
        kw = (kw or "").strip()
        if not kw:
            continue
        kw_toks = tokenize(kw)
        if not kw_toks:
            continue
        if kw_toks[0] not in tokens:
            return False
    return True


def _hard_filter_any_tokens(text: str, must_include_any: List[str]) -> bool:
    if not must_include_any:
        return True

    tokens = set(tokenize(text))
    for kw in must_include_any:
        kw = (kw or "").strip()
        if not kw:
            continue
        kw_toks = tokenize(kw)
        if not kw_toks:
            continue
        if kw_toks[0] in tokens:
            return True
    return False


def _slice_quote(text: str, query_tokens: List[str], max_chars: int = 700) -> str:
    """Return a short quote centered around the first matching query token."""
    raw = (text or "").strip()
    if not raw:
        return ""

    norm = normalize_arabic(raw)

    hit_pos = None
    for t in query_tokens:
        if not t:
            continue
        p = norm.find(t)
        if p != -1:
            hit_pos = p
            break

    if hit_pos is None:
        return raw[:max_chars].strip()

    start = max(0, hit_pos - max_chars // 3)
    end = min(len(raw), start + max_chars)

    snippet = raw[start:end].strip()

    if start > 0:
        snippet = "… " + snippet
    if end < len(raw):
        snippet = snippet + " …"

    return snippet


def _norm_contains(hay: str, needle: str) -> bool:
    hay_n = normalize_arabic(hay or "")
    nee_n = normalize_arabic(needle or "")
    return bool(nee_n) and (nee_n in hay_n)


def _match_section(ch: Dict[str, Any], section_hint: str | None) -> bool:
    if not section_hint:
        return True
    sec = ch.get("section") or ""
    txt = ch.get("text") or ""
    return _norm_contains(sec, section_hint) or _norm_contains(txt, section_hint)


def _exclude_by_hints(ch: Dict[str, Any], exclude_hints: List[str]) -> bool:
    if not exclude_hints:
        return False
    sec = ch.get("section") or ""
    txt = ch.get("text") or ""
    for h in exclude_hints:
        if _norm_contains(sec, h) or _norm_contains(txt, h):
            return True
    return False


def retrieve_evidence(
    evidence_query: Dict[str, Any],
    top_k: int = config.DEFAULT_TOP_K,
    min_score: float = config.DEFAULT_MIN_SCORE,
) -> List[Dict[str, Any]]:
    """
    Return evidence hits:
      {score, doc, source, chunk_id, page, section, quote}

    Optional strict filters:
      - must_include_keywords     -> AND tokens
      - must_include_any_keywords -> OR tokens
      - section_hint / exclude_hints
      - boost_keywords
    """
    q = build_query(evidence_query)
    if not q:
        return []

    doc_name = (evidence_query or {}).get("doc") or ""
    paths = _chunks_paths_by_doc(doc_name)

    query_tokens = tokenize(q)
    if not query_tokens:
        return []

    must_all = (evidence_query or {}).get("must_include_keywords") or []
    must_any = (evidence_query or {}).get("must_include_any_keywords") or []

    hits: List[Tuple[float, Dict[str, Any]]] = []

    for path in paths:
        chunks = _load_chunks(path)

        section_hint = (evidence_query or {}).get("section_hint")
        exclude_hints = (evidence_query or {}).get("exclude_hints") or []

        filtered_chunks = [
            ch for ch in chunks
            if _match_section(ch, section_hint)
            and not _exclude_by_hints(ch, exclude_hints)
            and _hard_filter_all_tokens(ch.get("text", ""), must_all)
            and _hard_filter_any_tokens(ch.get("text", ""), must_any)
        ]

        if not filtered_chunks:
            filtered_chunks = chunks

        docs_tokens = [tokenize(ch.get("text", "")) for ch in filtered_chunks]
        scores = _bm25_rank(query_tokens, docs_tokens)

        for ch, sc in zip(filtered_chunks, scores):
            if sc < min_score:
                continue

            full_text = ch.get("text") or ""
            quote = _slice_quote(full_text, query_tokens, max_chars=700)

            hits.append(
                (sc, {
                    "score": sc,
                    "doc": ch.get("doc_id") or doc_name,
                    "source": ch.get("source"),
                    "chunk_id": ch.get("chunk_id"),
                    "page": ch.get("page"),
                    "section": ch.get("section"),
                    "quote": quote,
                })
            )

    boost = evidence_query.get("boost_keywords") or []
    boost_norm = [normalize_arabic(x) for x in boost if x]

    def boosted_score(hit: Dict[str, Any]) -> float:
        qn = normalize_arabic(hit.get("quote", ""))
        extra = 0.0
        for b in boost_norm:
            if b and b in qn:
                extra += 2.0
        return float(hit.get("score", 0.0)) + extra

    hits.sort(key=lambda x: boosted_score(x[1]), reverse=True)
    return [h[1] for h in hits[:top_k]]
