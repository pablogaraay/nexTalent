"""Conservative exact-first mapping against the O*NET technology taxonomy."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable, Dict


TECHNOLOGY_SEMANTIC_LIMIT = 0.86
TECHNOLOGY_STRONG_SCORE = 0.92
TECHNOLOGY_MIN_MARGIN = 0.06
TECHNOLOGY_QUERY_RESULTS = 10


def normalize_technology_term(value: str) -> str:
  value = unicodedata.normalize("NFKD", str(value or ""))
  value = "".join(char for char in value if not unicodedata.combining(char)).casefold()
  value = re.sub(r"[^a-z0-9+#.]+", " ", value)
  return " ".join(value.split())


def build_exact_technology_index(collection) -> Dict[str, Dict[str, Any]]:
  result = collection.get(include=["metadatas"])
  owners: Dict[str, list[Dict[str, Any]]] = {}
  for metadata in result.get("metadatas", []) or []:
    metadata = metadata or {}
    terms = [metadata.get("preferred_label", "")]
    terms.extend(str(metadata.get("aliases", "") or "").split(" | "))
    for term in terms:
      key = normalize_technology_term(term)
      if key:
        owners.setdefault(key, []).append(metadata)

  # Conflicting aliases are deliberately omitted so exact matching abstains.
  return {
    term: candidates[0]
    for term, candidates in owners.items()
    if len({candidate.get("technology_id") for candidate in candidates}) == 1
  }


def match_technology(
  collection,
  text: str,
  embed_fn: Callable[[str], list[float]],
  *,
  exact_index: Dict[str, Dict[str, Any]] | None = None,
  limit: float = TECHNOLOGY_SEMANTIC_LIMIT,
  min_margin: float = TECHNOLOGY_MIN_MARGIN,
  strong_score: float = TECHNOLOGY_STRONG_SCORE,
  n_results: int = TECHNOLOGY_QUERY_RESULTS,
  allow_semantic: bool = True,
) -> Dict[str, Any]:
  text = str(text or "").strip()
  if not text:
    return {"status": "unmapped", "top1": None, "candidates": [], "margin": None}

  exact_metadata = (exact_index or {}).get(normalize_technology_term(text))
  if exact_metadata:
    top1 = {"metadata": exact_metadata, "score": 1.0}
    return {
      "status": "mapped",
      "top1": top1,
      "candidates": [top1],
      "margin": 1.0,
      "method": "exact_label_or_alias",
    }

  if not allow_semantic:
    return {"status": "unmapped", "top1": None, "candidates": [], "margin": None}

  result = collection.query(
    query_embeddings=[embed_fn(f"technology: {text}")],
    n_results=n_results,
    include=["metadatas", "distances"],
  )
  metadatas = (result.get("metadatas") or [[]])[0]
  distances = (result.get("distances") or [[]])[0]
  candidates = [
    {"metadata": metadata or {}, "score": 1 - float(distance)}
    for metadata, distance in zip(metadatas, distances)
  ]
  candidates.sort(key=lambda item: item["score"], reverse=True)
  if not candidates:
    return {"status": "unmapped", "top1": None, "candidates": [], "margin": None}

  top1 = candidates[0]
  margin = top1["score"] - candidates[1]["score"] if len(candidates) > 1 else 1.0
  above_limit = top1["score"] >= limit
  sufficiently_distinct = margin >= min_margin or top1["score"] >= strong_score
  status = "mapped" if above_limit and sufficiently_distinct else "ambiguous" if above_limit else "unmapped"
  return {
    "status": status,
    "top1": top1,
    "candidates": candidates[:3],
    "margin": margin,
    "method": "semantic",
  }
