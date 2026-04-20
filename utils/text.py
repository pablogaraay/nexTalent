from __future__ import annotations

from typing import Any, Dict, Iterable, List


def normalize_text(text: str) -> str:
  return (text or "").strip().lower()


def is_unknown_value(value: str) -> bool:
  v = normalize_text(value)
  return v in {"", "unknown", "unk", "none", "null", "n/a", "na", "desconocido"}


def unique_keep_order(items: Iterable[str]) -> List[str]:
  seen = set()
  out = []
  for item in items:
    clean = (item or "").strip()
    if not clean:
      continue
    key = normalize_text(clean)
    if key and key not in seen:
      seen.add(key)
      out.append(clean)
  return out


def offer_location_string(offer: Dict[str, Any]) -> str:
  parts = [
    str(offer.get("city", "") or "").strip(),
    str(offer.get("region", "") or "").strip(),
    str(offer.get("country", "") or "").strip(),
    str(offer.get("location_raw", "") or "").strip(),
  ]
  return " | ".join([part for part in parts if part])
