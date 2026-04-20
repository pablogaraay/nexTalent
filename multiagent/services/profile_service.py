from __future__ import annotations

import json
from typing import Any, Dict, List

import schemas
from utils.text import is_unknown_value, unique_keep_order

from ..cv_parser import read_cv_file
from ..llm_client import LLMClientService


SENIORITY_RAW_LEVELS = [
  "practicas",
  "prácticas",
  "junior",
  "intermedio",
  "mid",
  "senior",
  "lead",
  "manager",
  "director",
  "unknown",
]


class ProfileService:
  def __init__(self, llm_client_service: LLMClientService | None = None):
    self.llm_client_service = llm_client_service or LLMClientService()

  def _parse_profile_with_llm(self, text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
      return {
        "role": "",
        "skills": [],
        "seniority_raw": "unknown",
        "seniority_raw_targets": [],
        "location_query": "",
        "location_targets": [],
      }
    text = text[:12000]

    schema = schemas.build_profile_parse_schema(SENIORITY_RAW_LEVELS)

    system_prompt = f"""
      1. CONTEXTO
      Eres un experto en extracción de información estructurada a partir de perfiles profesionales.
      Tu tarea es analizar un texto de usuario (prompt libre y/o CV) y extraer campos de forma precisa.

      2. INSTRUCCIONES
      Debes extraer exactamente estos campos: role, skills, seniority_raw, seniority_raw_targets, location_query, location_targets

      Criterios principales:
      - role: Debe ser un rol profesional objetivo. Sin estados académicos.
      - skills: Lista de habilidades mencionadas explícitamente.
      - seniority_raw: Debe mapearse a {SENIORITY_RAW_LEVELS}
      - location_query: Texto breve con la ubicación deseada.
      - location_targets: Lista de ciudades/países/regiones extraídas.

      3. FORMATO
      Devuelve siempre un JSON estrictamente ligado al formato solicitado. No dejes keys fuera ni uses valores inventados.
    """

    user_prompt = (
      "Analiza el siguiente perfil y devuelve UNICAMENTE el JSON solicitado.\n\n"
      f"{text}"
    )

    parsed = self.llm_client_service.call_structured_extraction(system_prompt, user_prompt, schema)

    return {
      "role": (parsed.get("role") or "").strip(),
      "skills": unique_keep_order([str(item) for item in (parsed.get("skills") or [])]),
      "seniority_raw": (parsed.get("seniority_raw") or "unknown"),
      "seniority_raw_targets": unique_keep_order([str(item) for item in (parsed.get("seniority_raw_targets") or [])]),
      "location_query": (parsed.get("location_query") or "").strip(),
      "location_targets": unique_keep_order([str(item) for item in (parsed.get("location_targets") or [])]),
    }

  def parse_profile(self, profile_text: str = "", cv_file: str = "") -> Dict[str, Any]:
    cv_text = read_cv_file(cv_file) if cv_file else ""
    combined = "\n".join([profile_text or "", cv_text or ""]).strip()
    if not combined:
      raise ValueError("Debes enviar un prompt de perfil o un CV.")

    llm_profile = self._parse_profile_with_llm(combined)
    seniority_raw = "unknown" if is_unknown_value(llm_profile.get("seniority_raw", "")) else llm_profile.get("seniority_raw", "unknown")
    seniority_targets = [
      str(x) for x in (llm_profile.get("seniority_raw_targets", []) or [])
      if not is_unknown_value(str(x))
    ]
    return {
      "role": "" if is_unknown_value(llm_profile.get("role", "")) else llm_profile.get("role", ""),
      "role_candidates": [],
      "skills": llm_profile.get("skills", []),
      "seniority_raw": seniority_raw,
      "seniority_raw_targets": unique_keep_order(seniority_targets),
      "search_intent": "unclear",
      "location_query": llm_profile.get("location_query", ""),
      "location_targets": llm_profile.get("location_targets", []),
      "raw_text": combined,
      "source": {
        "profile_text_present": bool(profile_text.strip()),
        "cv_file": cv_file or "",
        "cv_loaded": bool(cv_text.strip()),
        "parse_method": "llm",
      },
    }

  def assess_profile_signal(self, profile: Dict[str, Any]) -> Dict[str, Any]:
    role = str(profile.get("role", "") or "").strip()
    skills = [str(x).strip() for x in (profile.get("skills") or []) if str(x).strip()]
    seniority = str(profile.get("seniority_raw", "unknown") or "unknown").strip()
    location_query = str(profile.get("location_query", "") or "").strip()
    location_targets = [str(x).strip() for x in (profile.get("location_targets") or []) if str(x).strip()]
    raw_text = str(profile.get("raw_text", "") or "").strip()

    score = 0.0
    reasons = []

    if role and not is_unknown_value(role):
      score += 0.4
    else:
      reasons.append("falta_rol_claro")

    if len(skills) >= 3:
      score += 0.3
    elif skills:
      score += 0.15
      reasons.append("pocas_skills")
    else:
      reasons.append("falta_skills")

    if seniority and not is_unknown_value(seniority):
      score += 0.15
    else:
      reasons.append("falta_seniority")

    if location_query or location_targets:
      score += 0.1
    else:
      reasons.append("falta_ubicacion")

    if len(raw_text) >= 200:
      score += 0.05

    if score >= 0.65:
      level = "strong"
    elif score >= 0.4:
      level = "medium"
    else:
      level = "weak"

    return {
      "score": round(score, 4),
      "level": level,
      "reasons": reasons,
    }

  def enrich_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
    current = dict(profile or {})
    raw_text = str(current.get("raw_text", "") or "").strip()
    if not raw_text:
      current.setdefault("role_candidates", [])
      current.setdefault("search_intent", "unclear")
      return current

    schema = schemas.build_profile_enrichment_schema(SENIORITY_RAW_LEVELS)
    system_prompt = f"""
      1. CONTEXTO
      Eres un experto en reinterpretación de perfiles profesionales para búsqueda de empleo.

      2. INSTRUCCIONES
      Debes mejorar el perfil sin inventar experiencia:
      - role: rol principal si existe señal.
      - role_candidates: hasta 5 roles cercanos y empleables.
      - skills: skills explícitas o claramente inferibles.
      - seniority_raw: mapear a {SENIORITY_RAW_LEVELS}
      - search_intent: strict | exploratory | unclear
      - location_query y location_targets: solo si hay señal real.

      3. RESTRICCIONES
      - No inventes logros ni experiencia no presente.
      - Si hay ambigüedad, usa search_intent='exploratory'.
      - Devuelve únicamente JSON válido con el schema solicitado.
    """
    user_prompt = (
      "Reinterpreta el perfil para mejorar la búsqueda de empleo.\n\n"
      f"Perfil actual:\n{json.dumps(current, ensure_ascii=False, indent=2)}\n\n"
      f"Texto original:\n{raw_text}"
    )

    parsed = self.llm_client_service.call_structured_extraction(system_prompt, user_prompt, schema)

    merged = dict(current)
    parsed_role = str(parsed.get("role", "") or "").strip()
    if parsed_role and not is_unknown_value(parsed_role):
      merged["role"] = parsed_role

    merged["role_candidates"] = unique_keep_order([str(x) for x in (parsed.get("role_candidates") or [])])[:5]
    merged["skills"] = unique_keep_order(
      [str(x) for x in (merged.get("skills") or [])] +
      [str(x) for x in (parsed.get("skills") or [])]
    )

    parsed_seniority = str(parsed.get("seniority_raw", "unknown") or "unknown").strip()
    merged["seniority_raw"] = parsed_seniority if not is_unknown_value(parsed_seniority) else merged.get("seniority_raw", "unknown")
    if is_unknown_value(str(merged.get("seniority_raw", "unknown"))):
      merged["seniority_raw_targets"] = []
    else:
      merged["seniority_raw_targets"] = [str(merged.get("seniority_raw"))]

    merged["search_intent"] = str(parsed.get("search_intent", "unclear") or "unclear").strip()

    parsed_location_query = str(parsed.get("location_query", "") or "").strip()
    if parsed_location_query:
      merged["location_query"] = parsed_location_query

    merged["location_targets"] = unique_keep_order(
      [str(x) for x in (merged.get("location_targets") or [])] +
      [str(x) for x in (parsed.get("location_targets") or [])]
    )

    merged_source = dict(merged.get("source") or {})
    merged_source["enrichment_method"] = "llm_reinterpretation"
    merged["source"] = merged_source
    return merged
