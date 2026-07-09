from __future__ import annotations
import json
from typing import Any, Dict, List
import schemas
from config import Config
from repositories.vector_store import VectorStore
from utils.text import is_unknown_value, unique_keep_order
from ..cv_parser import read_cv_file
from ..llm_client import LLMClientService

NORMALIZED_ROLE_LIMIT = 0.60

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
  def __init__(
    self,
    llm_client_service: LLMClientService | None = None,
    vector_store: VectorStore | None = None,
  ):
    self.llm_client_service = llm_client_service or LLMClientService()
    self.vector_store = vector_store or VectorStore()

  @staticmethod
  def _clean_list(values) -> List[str]:
    return unique_keep_order([
      str(item).strip()
      for item in (values or [])
      if str(item or "").strip() and not is_unknown_value(str(item))
    ])

  @staticmethod
  def _normalize_seniority(value: str) -> str:
    seniority = str(value or "unknown").strip().lower()
    if seniority not in SENIORITY_RAW_LEVELS or is_unknown_value(seniority):
      return "unknown"
    return seniority

  def _clean_role_experiences(self, values) -> List[Dict[str, str]]:
    experiences = []
    seen = set()
    for item in values or []:
      if not isinstance(item, dict):
        continue

      role = str(item.get("role", "") or "").strip()
      if not role or is_unknown_value(role):
        continue

      experience = {
        "role": role,
        "seniority_raw": self._normalize_seniority(item.get("seniority_raw", "unknown")),
        "location": str(item.get("location", "") or "").strip(),
      }
      key = (
        experience["role"].casefold(),
        experience["seniority_raw"],
        experience["location"].casefold(),
      )
      if key in seen:
        continue
      seen.add(key)
      experiences.append(experience)

    return experiences

  def _best_normalized_role(self, role: str, collection=None) -> Dict[str, Any] | None:
    role = str(role or "").strip()
    if not role:
      return None

    collection = collection or self.vector_store.get_collection(Config.JOBS_CHROMA_COLLECTION)
    embedding = self.llm_client_service.embed_text(f"occupation: {role}")
    result = collection.query(
      query_embeddings=[embedding],
      n_results=3,
      include=["metadatas", "distances"]
    )
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    if not metadatas or not distances:
      return None

    metadata = metadatas[0] or {}
    score = 1 - float(distances[0])
    if score < NORMALIZED_ROLE_LIMIT:
      return None

    occupation = str(metadata.get("occupation", "") or "").strip()
    if not occupation:
      return None

    return {
      "occupation": occupation,
      "score": round(score, 4),
    }

  def _aggregate_normalized_roles(self, role_experiences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized_by_occupation: Dict[str, Dict[str, Any]] = {}
    for experience in role_experiences or []:
      occupation = str(experience.get("normalized_occupation", "") or "").strip()
      if not occupation:
        continue

      role = str(experience.get("role", "") or "").strip()
      score = float(experience.get("normalized_score", 0.0) or 0.0)
      current = normalized_by_occupation.get(occupation)
      if current is None:
        normalized_by_occupation[occupation] = {
          "occupation": occupation,
          "source_roles": [role] if role else [],
          "score": round(score, 4),
        }
      else:
        current["source_roles"] = unique_keep_order(current["source_roles"] + ([role] if role else []))
        current["score"] = round(max(float(current.get("score", 0.0) or 0.0), score), 4)

    return sorted(
      normalized_by_occupation.values(),
      key=lambda item: float(item.get("score", 0.0) or 0.0),
      reverse=True
    )

  def _build_role_experience_analysis(
    self,
    role_experiences: List[Dict[str, Any]],
    performed_roles: List[str],
    fallback_seniority: str,
    fallback_location: str,
  ) -> List[Dict[str, Any]]:
    clean_experiences = self._clean_role_experiences(role_experiences)
    existing_roles = {item["role"].casefold() for item in clean_experiences}
    for role in self._clean_list(performed_roles):
      if role.casefold() in existing_roles:
        continue
      clean_experiences.append({
        "role": role,
        "seniority_raw": fallback_seniority,
        "location": fallback_location,
      })
      existing_roles.add(role.casefold())

    try:
      collection = self.vector_store.get_collection(Config.JOBS_CHROMA_COLLECTION)
      for experience in clean_experiences:
        normalized = self._best_normalized_role(experience.get("role", ""), collection=collection)
        if normalized:
          experience["normalized_occupation"] = normalized["occupation"]
          experience["normalized_score"] = normalized["score"]
    except Exception as exc:
      if getattr(Config, "AUTONOMOUS_AGENT_VERBOSE", False):
        print(f"Profile role taxonomy mapping unavailable: {exc}")

    return clean_experiences

  def _map_performed_roles_to_jobs(self, performed_roles: List[str]) -> List[Dict[str, Any]]:
    clean_roles = self._clean_list(performed_roles)
    if not clean_roles:
      return []

    try:
      collection = self.vector_store.get_collection(Config.JOBS_CHROMA_COLLECTION)
      role_experiences = []
      for role in clean_roles:
        normalized = self._best_normalized_role(role, collection=collection)
        if normalized:
          role_experiences.append({
            "role": role,
            "normalized_occupation": normalized["occupation"],
            "normalized_score": normalized["score"],
          })
    except Exception as exc:
      if getattr(Config, "AUTONOMOUS_AGENT_VERBOSE", False):
        print(f"Profile role taxonomy mapping unavailable: {exc}")
      return []

    return self._aggregate_normalized_roles(role_experiences)

  def _parse_profile_with_llm(self, text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
      return {
        "role": "",
        "performed_roles": [],
        "role_experiences": [],
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
      Debes extraer exactamente estos campos: role, performed_roles, role_experiences, skills, seniority_raw, seniority_raw_targets, location_query, location_targets

      Criterios principales:
      - role: Debe ser un rol profesional objetivo. Sin estados académicos.
      - performed_roles: Lista de todos los cargos, roles o funciones profesionales que el candidato haya desempeñado realmente.
        No incluyas roles objetivo ni aspiracionales si no hay evidencia en el texto.
      - role_experiences: Lista correlacionada de experiencias. Para cada rol desempeñado, incluye:
        role, seniority_raw asociado a ese rol y location asociada si aparece. Usa unknown o "" si no hay evidencia.
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
      "performed_roles": self._clean_list(parsed.get("performed_roles") or []),
      "role_experiences": self._clean_role_experiences(parsed.get("role_experiences") or []),
      "skills": self._clean_list(parsed.get("skills") or []),
      "seniority_raw": (parsed.get("seniority_raw") or "unknown"),
      "seniority_raw_targets": self._clean_list(parsed.get("seniority_raw_targets") or []),
      "location_query": (parsed.get("location_query") or "").strip(),
      "location_targets": self._clean_list(parsed.get("location_targets") or []),
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
    role = "" if is_unknown_value(llm_profile.get("role", "")) else llm_profile.get("role", "")
    performed_roles = self._clean_list(llm_profile.get("performed_roles") or [])
    if role:
      performed_roles = unique_keep_order([role] + performed_roles)
    role_experiences = self._build_role_experience_analysis(
      role_experiences=llm_profile.get("role_experiences") or [],
      performed_roles=performed_roles,
      fallback_seniority=seniority_raw,
      fallback_location=llm_profile.get("location_query", ""),
    )

    return {
      "role": role,
      "performed_roles": performed_roles,
      "role_experiences": role_experiences,
      "normalized_roles": self._aggregate_normalized_roles(role_experiences),
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
      current.setdefault("performed_roles", [])
      current.setdefault("role_experiences", [])
      current.setdefault("normalized_roles", [])
      current.setdefault("search_intent", "unclear")
      return current

    schema = schemas.build_profile_enrichment_schema(SENIORITY_RAW_LEVELS)
    system_prompt = f"""
      1. CONTEXTO
      Eres un experto en reinterpretación de perfiles profesionales para búsqueda de empleo.

      2. INSTRUCCIONES
      Debes mejorar el perfil sin inventar experiencia:
      - role: rol principal si existe señal.
      - performed_roles: todos los cargos, roles o funciones profesionales desempeñados realmente por el candidato.
      - role_experiences: lista correlacionada de roles desempeñados con seniority_raw y location propios de cada rol.
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

    merged["performed_roles"] = unique_keep_order(
      self._clean_list([merged.get("role", "")]) +
      self._clean_list(merged.get("performed_roles") or []) +
      self._clean_list(parsed.get("performed_roles") or [])
    )

    parsed_seniority = str(parsed.get("seniority_raw", "unknown") or "unknown").strip()
    merged["seniority_raw"] = parsed_seniority if not is_unknown_value(parsed_seniority) else merged.get("seniority_raw", "unknown")
    if is_unknown_value(str(merged.get("seniority_raw", "unknown"))):
      merged["seniority_raw_targets"] = []
    else:
      merged["seniority_raw_targets"] = [str(merged.get("seniority_raw"))]

    parsed_location_query = str(parsed.get("location_query", "") or "").strip()
    if parsed_location_query:
      merged["location_query"] = parsed_location_query

    merged["location_targets"] = unique_keep_order(
      [str(x) for x in (merged.get("location_targets") or [])] +
      [str(x) for x in (parsed.get("location_targets") or [])]
    )

    merged["role_experiences"] = self._build_role_experience_analysis(
      role_experiences=(merged.get("role_experiences") or []) + (parsed.get("role_experiences") or []),
      performed_roles=merged["performed_roles"],
      fallback_seniority=str(merged.get("seniority_raw", "unknown") or "unknown"),
      fallback_location=str(merged.get("location_query", "") or ""),
    )
    merged["normalized_roles"] = self._aggregate_normalized_roles(merged["role_experiences"])
    merged["role_candidates"] = unique_keep_order([str(x) for x in (parsed.get("role_candidates") or [])])[:5]
    merged["skills"] = unique_keep_order(
      [str(x) for x in (merged.get("skills") or [])] +
      [str(x) for x in (parsed.get("skills") or [])]
    )

    merged["search_intent"] = str(parsed.get("search_intent", "unclear") or "unclear").strip()

    merged_source = dict(merged.get("source") or {})
    merged_source["enrichment_method"] = "llm_reinterpretation"
    merged["source"] = merged_source
    return merged
