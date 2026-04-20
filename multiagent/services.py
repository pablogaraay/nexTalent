from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List
from datetime import datetime, timezone
import json
from chromadb import PersistentClient

try:
  from config import Config
  from dbConn import MongoManager
  import schemas
except ModuleNotFoundError:
  import sys
  BASE_DIR = Path(__file__).resolve().parent.parent
  if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
  from config import Config
  from dbConn import MongoManager
  import schemas

from .cv_parser import read_cv_file
from .llm_client import LLMClientService

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
  "unknown"
]

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
    str(offer.get("location_raw", "") or "").strip()
  ]
  return " | ".join([part for part in parts if part])


class UseCaseService:
  def __init__(self):
    self.llm_client_service = LLMClientService()
    self._job_title_map: Dict[str, str] | None = None

  def load_offers_for_analysis(self) -> List[Dict[str, Any]]:
    db = MongoManager()
    try:
      return db.load_offers(Config.MAPPED_COLL) or []
    finally:
      db.close_connection()

  def _parse_profile_with_llm(self, text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
      return {
        "role": "",
        "skills": [],
        "seniority_raw": "unknown",
        "seniority_raw_targets": [],
        "location_query": "",
        "location_targets": []
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
      "location_targets": unique_keep_order([str(item) for item in (parsed.get("location_targets") or [])])
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
        "parse_method": "llm"
      }
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
      "reasons": reasons
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

  @staticmethod
  def _default_search_plan() -> Dict[str, Any]:
    return {
      "strategy": "llm_rerank",
      "confidence": 0.5,
      "reasons": ["default_plan"],
      "use_location_priority": True,
      "use_seniority_priority": True,
      "top_k_hint": int(getattr(Config, "RETRIEVAL_TOP_K", 50))
    }

  def _build_autonomous_planner_prompts(self, profile: Dict[str, Any]) -> tuple[str, str]:
    system_prompt = """
      1. CONTEXTO

      Eres un planificador autónomo de búsqueda de empleo.
      Tu tarea es decidir la estrategia de ranking más adecuada en función del perfil del usuario usando tool-calling.

      2. INSTRUCCIONES

      Debes analizar señales del perfil:
      - role
      - skills
      - seniority_raw
      - location_query / location_targets

      Debes devolver una estrategia entre:
      - llm_rerank
      - vector_only
      - no_match

      Criterios:
      - Si hay información útil suficiente (rol y/o skills relevantes), favorece llm_rerank.
      - Si la información es parcial o ambigua, considera vector_only.
      - Si no hay información útil para recomendar con calidad, usa no_match.
      - Si existe ubicación explícita, activa use_location_priority=true.
      - Si existe seniority explícito, activa use_seniority_priority=true.

      3. TOOL CALLING

      Debes llamar exactamente UNA herramienta:
      - run_llm_rerank
      - run_vector_only
      - run_no_match

      Pasa en los argumentos:
      - confidence (0..1)
      - reasons (lista breve, en español)
      - use_location_priority (boolean)
      - use_seniority_priority (boolean)
      - top_k_hint (5..200)

      4. RESTRICCIONES

      - No devuelvas texto libre; usa tool-calling.
      - No inventes información que no esté en el perfil.
      - confidence debe estar en rango [0,1].
      - reasons debe ser breve y concreta.
      - reasons debe estar en español.
    """

    profile_payload = {
      "role": profile.get("role", ""),
      "skills": profile.get("skills", []),
      "seniority_raw": profile.get("seniority_raw", "unknown"),
      "seniority_raw_targets": profile.get("seniority_raw_targets", []),
      "location_query": profile.get("location_query", ""),
      "location_targets": profile.get("location_targets", [])
    }
    user_prompt = (
      "Analiza el siguiente perfil y selecciona una herramienta para decidir la estrategia de búsqueda.\n\n"
      f"{json.dumps(profile_payload, ensure_ascii=False, indent=2)}"
    )
    return system_prompt, user_prompt

  def _coerce_search_plan(self, raw_plan: Dict[str, Any]) -> Dict[str, Any]:
    plan = self._default_search_plan()
    if not isinstance(raw_plan, dict):
      return plan

    strategy = str(raw_plan.get("strategy", "") or "").strip()
    allowed = {"llm_rerank", "vector_only", "no_match"}
    if strategy in allowed:
      plan["strategy"] = strategy

    try:
      confidence = float(raw_plan.get("confidence", plan["confidence"]))
      plan["confidence"] = max(0.0, min(1.0, confidence))
    except Exception:
      pass

    reasons = unique_keep_order([str(x) for x in (raw_plan.get("reasons") or [])])[:5]
    if reasons:
      plan["reasons"] = reasons

    plan["use_location_priority"] = bool(raw_plan.get("use_location_priority", plan["use_location_priority"]))
    plan["use_seniority_priority"] = bool(raw_plan.get("use_seniority_priority", plan["use_seniority_priority"]))

    try:
      top_k_hint = int(raw_plan.get("top_k_hint", plan["top_k_hint"]))
      plan["top_k_hint"] = max(5, min(200, top_k_hint))
    except Exception:
      pass

    return plan

  def decide_search_plan(self, profile: Dict[str, Any]) -> Dict[str, Any]:
    base_plan = self._default_search_plan()
    try:
      system_prompt, user_prompt = self._build_autonomous_planner_prompts(profile or {})
      tool_result = self.llm_client_service.call_autonomous_strategy_tool(system_prompt, user_prompt)
      tool_name = str((tool_result or {}).get("tool_name", "") or "").strip()
      raw_args = (tool_result or {}).get("arguments", {}) or {}

      strategy_map = {
        "run_llm_rerank": "llm_rerank",
        "run_vector_only": "vector_only",
        "run_no_match": "no_match"
      }

      if tool_name in strategy_map:
        raw_plan = {
          **raw_args,
          "strategy": strategy_map[tool_name]
        }
        source = "llm_tool_calling"
      else:
        # Si no hay tool_call válido, aplicamos plan por defecto.
        raw_plan = base_plan
        source = "default_plan_no_tool_call"

      plan = self._coerce_search_plan(raw_plan)
      return {
        **plan,
        "source": source
      }
    except Exception as exc:
      if getattr(Config, "AUTONOMOUS_AGENT_VERBOSE", False):
        print(f"Autonomous planner fallback to default plan: {exc}")
      return {**base_plan, "source": "fallback_default"}

  @staticmethod
  def offer_skills(offer: Dict[str, Any]) -> List[str]:
    raw: List[str] = []
    raw.extend(offer.get("hard_skills_raw", []) or [])
    raw.extend(offer.get("soft_skills_raw", []) or [])
    raw.extend(offer.get("tools_raw", []) or [])
    raw.extend([(item or {}).get("skill_name", "") for item in (offer.get("skills_sfia", []) or [])])
    return unique_keep_order([str(item) for item in raw])[:12]

  def _offer_for_llm(self, offer: Dict[str, Any], custom_id: str) -> Dict[str, Any]:
    return {
      "offer_id": custom_id,
      "title": offer.get("title", ""),
      "company": offer.get("company", ""),
      "role_raw": offer.get("role_raw", ""),
      "seniority_raw": offer.get("seniority_raw", ""),
      "city": offer.get("city", ""),
      "region": offer.get("region", ""),
      "country": offer.get("country", ""),
      "skills": self.offer_skills(offer)
    }

  def _retrieve_candidates_vector(
    self,
    profile: Dict[str, Any],
    all_offers: List[Dict[str, Any]],
    top_k: int,
    use_location_priority: bool = True,
    use_seniority_priority: bool = True
  ) -> List[Dict[str, Any]]:
    parts = []
    role = (profile.get("role") or "").strip()
    if role and not is_unknown_value(role):
      parts.append(f"role: {role}")
    role_candidates = [str(x).strip() for x in (profile.get("role_candidates") or []) if str(x).strip()]
    if role_candidates:
      parts.append(f"related_roles: {', '.join(role_candidates[:3])}")
    seniority = (profile.get("seniority_raw") or "").strip()
    if use_seniority_priority and seniority and not is_unknown_value(seniority):
      parts.append(f"seniority: {seniority}")
    skills = profile.get("skills") or []
    if skills: parts.append(f"skills: {', '.join(skills)}")
    location_query = (profile.get("location_query") or "").strip()
    if use_location_priority and location_query:
      parts.append(f"location: {location_query}")
    query_text = " | ".join(parts) if parts else ""
    if not query_text:
      return []

    base_dir = Path(__file__).resolve().parent.parent
    chroma_path = base_dir / "data/chroma"
    client = PersistentClient(path=str(chroma_path))
    
    try:
      collection = client.get_collection(Config.OFFERS_CHROMA_COLLECTION)
    except Exception:
      print("No se encontro la coleccion en ChromaDB. Regresando lista truncada.")
      return all_offers[:top_k]
    
    qv = self.llm_client_service.embed_text(query_text)
    location_targets = []
    if use_location_priority:
      location_targets = [normalize_text(str(x)) for x in (profile.get("location_targets") or []) if str(x).strip()]
    effective_top_k = min(len(all_offers), top_k * 4) if location_targets else top_k
    res = collection.query(query_embeddings=[qv], n_results=effective_top_k, include=["metadatas", "distances"])
    
    metas = res.get("metadatas", [[]])[0] if res.get("metadatas") else []
    dists = res.get("distances", [[]])[0] if res.get("distances") else []

    offers_by_url = {offer.get("url"): offer for offer in all_offers}
    
    retrieved = []
    for m, d in zip(metas, dists):
      url = m.get("url")
      if url and url in offers_by_url:
        offer = dict(offers_by_url[url])
        offer["vector_score"] = 1.0 - d
        retrieved.append(offer)

    if location_targets:
      location_filtered = []
      for offer in retrieved:
        loc = normalize_text(offer_location_string(offer))
        if any(target in loc for target in location_targets):
          location_filtered.append(offer)
      if location_filtered:
        remainder = [offer for offer in retrieved if offer not in location_filtered]
        retrieved = location_filtered + remainder

    return retrieved

  def _build_vector_only_results(self, top_candidates: List[Dict[str, Any]], profile: Dict[str, Any], top_n: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    profile_skills = {normalize_text(str(s)) for s in (profile.get("skills") or [])}
    min_vector_score = float(getattr(Config, "VECTOR_FALLBACK_MIN_SCORE", 0.6))
    strong_candidates = [offer for offer in top_candidates if float(offer.get("vector_score", 0.0)) >= min_vector_score]

    for offer in strong_candidates[:top_n]:
      offer_skills = [str(x) for x in self.offer_skills(offer)]
      matched = [s for s in offer_skills if normalize_text(s) in profile_skills]
      out.append({
        "url": offer.get("url", ""),
        "title": offer.get("title", ""),
        "company": offer.get("company", ""),
        "role_raw": offer.get("role_raw", ""),
        "location": offer_location_string(offer),
        "job_mapping": offer.get("job_mapping", {}),
        "match_score": round(float(offer.get("vector_score", 0.0)), 4),
        "matched_skills": unique_keep_order(matched),
        "why_match": "Coincidencia semántica por embeddings",
        "vector_score": round(float(offer.get("vector_score", 0.0)), 4)
      })
    return out

  def _rerank_final_with_llm(self, profile: Dict[str, Any], finalists: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
    prompt = {
      "profile": {
        "role": profile.get("role", ""),
        "skills": profile.get("skills", []),
        "seniority_raw": profile.get("seniority_raw", "unknown"),
        "seniority_raw_targets": profile.get("seniority_raw_targets", []),
        "location_query": profile.get("location_query", ""),
        "location_targets": profile.get("location_targets", [])
      },
      "instructions": {
        "objective": f"Elegir top {top_n} final.",
        "rules": [
          "Prioriza ajuste global (rol + skills + seniority).",
          "Si location_targets no está vacío, prioriza fuertemente ofertas en esas ubicaciones (city/region/country).",
          "Devuelve un JSON con campo 'ranked'.",
          f"Devuelve como maximo {top_n} elementos.",
          "Cada elemento de ranked debe incluir: offer_id (string, exact matching), score (0..1), matched_skills (array de strings)."
        ]
      },
      "offers": finalists
    }
    raw_ranked = self.llm_client_service.call_reranker(prompt, top_n)
    return self._coerce_ranked_items(raw_ranked)

  @staticmethod
  def _coerce_ranked_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for item in items or []:
      offer_id = str((item or {}).get("offer_id", "")).strip()
      if not offer_id:
        continue
      try:
        score = float((item or {}).get("score", 0))
      except Exception:
        score = 0.0
      score = max(0.0, min(1.0, score))
      matched = unique_keep_order([str(s) for s in ((item or {}).get("matched_skills") or [])])
      cleaned.append({"offer_id": offer_id, "score": score, "matched_skills": matched})
    return cleaned

  def use_case_search(
    self,
    offers: List[Dict[str, Any]],
    profile: Dict[str, Any],
    top_n: int = 10,
    plan: Dict[str, Any] | None = None
  ) -> Dict[str, Any]:
    if not offers:
      return {"profile": profile, "total_candidates": 0, "results": [], "agent": {}}

    active_plan = self._default_search_plan()
    if isinstance(plan, dict) and plan:
      active_plan = {
        **active_plan,
        **self._coerce_search_plan(plan),
        "source": plan.get("source", "llm")
      }

    strategy_requested = str(active_plan.get("strategy", "llm_rerank") or "llm_rerank").strip()
    strategy_applied = strategy_requested
    confidence = round(float(active_plan.get("confidence", 0.0)), 4)
    reasons = active_plan.get("reasons", [])
    source = active_plan.get("source", "")

    retrieval_k_default = int(getattr(Config, "RETRIEVAL_TOP_K", 50))
    retrieval_k = max(top_n, min(200, int(active_plan.get("top_k_hint", retrieval_k_default))))

    top_candidates = self._retrieve_candidates_vector(
      profile,
      offers,
      top_k=retrieval_k,
      use_location_priority=bool(active_plan.get("use_location_priority", True)),
      use_seniority_priority=bool(active_plan.get("use_seniority_priority", True))
    )

    if not top_candidates:
      return {
        "profile": profile,
        "total_candidates": len(offers),
        "results": [],
        "agent": {
          "strategy_requested": strategy_requested,
          "strategy_applied": strategy_applied,
          "confidence": confidence,
          "reasons": reasons,
          "source": source
        }
      }

    if strategy_applied == "no_match":
      return {
        "profile": profile,
        "total_candidates": len(offers),
        "results": [],
        "agent": {
          "strategy_requested": strategy_requested,
          "strategy_applied": strategy_applied,
          "confidence": confidence,
          "reasons": reasons,
          "source": source,
          "message": "No hay señal suficiente para recomendar ofertas con calidad."
        }
      }

    if strategy_applied == "vector_only":
      vector_results = self._build_vector_only_results(top_candidates, profile, top_n)
      return {
        "profile": profile,
        "total_candidates": len(offers),
        "results": vector_results,
        "agent": {
          "strategy_requested": strategy_requested,
          "strategy_applied": strategy_applied,
          "confidence": confidence,
          "reasons": reasons,
          "source": source
        }
      }

    rerank_candidates = int(getattr(Config, "RERANK_CANDIDATES", 20))
    rerank_candidates = max(top_n, rerank_candidates)

    candidates_for_rerank = top_candidates[:rerank_candidates]

    finalists_payload = []
    for idx, cand in enumerate(candidates_for_rerank):
      finalists_payload.append(self._offer_for_llm(cand, custom_id=str(idx)))

    final_ranked = self._rerank_final_with_llm(profile, finalists_payload, top_n=top_n)

    results = []

    if final_ranked:
      llm_min_score = float(getattr(Config, "LLM_MIN_MATCH_SCORE", 0.20))
      used_idx = set()
      for item in final_ranked:
        try:
          idx = int(item.get("offer_id", "-1"))
        except Exception:
          continue
        if idx < 0 or idx >= len(candidates_for_rerank) or idx in used_idx:
          continue
        if float(item.get("score", 0.0)) < llm_min_score:
          continue
        used_idx.add(idx)

        offer = candidates_for_rerank[idx]
        matched = unique_keep_order([str(s) for s in (item.get("matched_skills") or [])])
        results.append({
          "url": offer.get("url", ""),
          "title": offer.get("title", ""),
          "company": offer.get("company", ""),
          "role_raw": offer.get("role_raw", ""),
          "location": offer_location_string(offer),
          "job_mapping": offer.get("job_mapping", {}),
          "match_score": round(float(item.get("score", 0)), 4),
          "matched_skills": matched,
          "why_match": f"Reranked by LLM. Vector Sim: {round(offer.get('vector_score', 0), 4)}",
          "vector_score": round(offer.get('vector_score', 0), 4)
        })

    if not results:
      min_vector_score = float(getattr(Config, "VECTOR_FALLBACK_MIN_SCORE", 0.8))
      strong_candidates = [
        offer for offer in candidates_for_rerank
        if float(offer.get("vector_score", 0.0)) >= min_vector_score
      ]
      for idx, offer in enumerate(strong_candidates[:top_n]):
        results.append({
          "url": offer.get("url", ""),
          "title": offer.get("title", ""),
          "company": offer.get("company", ""),
          "role_raw": offer.get("role_raw", ""),
          "location": offer_location_string(offer),
          "job_mapping": offer.get("job_mapping", {}),
          "match_score": round(offer.get('vector_score', 0), 4),
          "matched_skills": [],
          "why_match": f"Vector Fallback Sim: {round(offer.get('vector_score', 0), 4)}",
          "vector_score": round(offer.get('vector_score', 0), 4)
        })

    return {
      "profile": profile,
      "total_candidates": len(offers),
      "results": results[:top_n],
      "agent": {
        "strategy_requested": strategy_requested,
        "strategy_applied": strategy_applied,
        "confidence": confidence,
        "reasons": reasons,
        "source": source
      }
    }

  @staticmethod
  def _safe_share(count: int, total: int) -> float:
    if total <= 0:
      return 0.0
    return round((count / total) * 100.0, 2)

  def _load_job_title_map(self) -> Dict[str, str]:
    if self._job_title_map is not None:
      return self._job_title_map

    base_dir = Path(__file__).resolve().parent.parent
    jobs_file = base_dir / "nexTalent.wef_jobs_taxonomy.json"
    out: Dict[str, str] = {}

    try:
      rows = json.loads(jobs_file.read_text(encoding="utf-8"))
      if isinstance(rows, list):
        for row in rows:
          job_id = str((row or {}).get("job_id", "")).strip()
          title = str((row or {}).get("occupation", "")).strip()
          if job_id and title:
            out[job_id] = title
    except Exception:
      out = {}

    self._job_title_map = out
    return out

  def use_case_market_insights(self, offers: List[Dict[str, Any]], top_n: int = 10) -> Dict[str, Any]:
    top_n = max(1, min(int(top_n), 100))
    total_offers = len(offers or [])
    job_title_map = self._load_job_title_map()

    offers_with_job_mapping = 0
    offers_with_skills_sfia = 0

    jobs_counter: Dict[tuple, int] = {}
    skills_counter: Dict[tuple, int] = {}

    for offer in offers or []:
      job_id = str(((offer.get("job_mapping") or {}).get("job_id_wef", "") or "")).strip()
      job_family = str(((offer.get("job_mapping") or {}).get("job_family_wef", "") or "")).strip()
      if job_id:
        offers_with_job_mapping += 1
        key = (job_id, job_family)
        jobs_counter[key] = jobs_counter.get(key, 0) + 1

      skills = offer.get("skills_sfia") or []
      if skills:
        offers_with_skills_sfia += 1

      # Evita duplicar la misma skill varias veces en la misma oferta.
      seen_skill_ids = set()
      for item in skills:
        skill_id = str(((item or {}).get("skill_id", "") or "")).strip()
        skill_name = str(((item or {}).get("skill_name", "") or "")).strip()
        if not skill_id or skill_id in seen_skill_ids:
          continue
        seen_skill_ids.add(skill_id)
        key = (skill_id, skill_name)
        skills_counter[key] = skills_counter.get(key, 0) + 1

    top_jobs = []
    for (job_id, job_family), demand in sorted(
      jobs_counter.items(), key=lambda x: x[1], reverse=True
    )[:top_n]:
      job_title = job_title_map.get(job_id, "")
      top_jobs.append({
        "job_id": job_id,
        "job_title": job_title if job_title else job_id,
        "job_family": job_family,
        "demand": demand,
        "share_total_offers_pct": self._safe_share(demand, total_offers)
      })

    top_skills = []
    for (skill_id, skill_name), demand in sorted(
      skills_counter.items(), key=lambda x: x[1], reverse=True
    )[:top_n]:
      top_skills.append({
        "skill_id": skill_id,
        "skill_name": skill_name,
        "demand": demand,
        "share_total_offers_pct": self._safe_share(demand, total_offers)
      })

    return {
      "generated_at_utc": datetime.now(timezone.utc).isoformat(),
      "collection": Config.MAPPED_COLL,
      "summary": {
        "total_offers": total_offers,
        "offers_with_job_mapping": offers_with_job_mapping,
        "offers_with_skills_sfia": offers_with_skills_sfia,
        "job_mapping_coverage_pct": self._safe_share(offers_with_job_mapping, total_offers),
        "skills_sfia_coverage_pct": self._safe_share(offers_with_skills_sfia, total_offers)
      },
      "top_jobs": top_jobs,
      "top_skills": top_skills
    }
