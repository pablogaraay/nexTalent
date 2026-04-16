from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List
from datetime import datetime, timezone
import json
from chromadb import PersistentClient

try:
  from config import Config
  from dbConn import MongoManager
except ModuleNotFoundError:
  import sys
  BASE_DIR = Path(__file__).resolve().parent.parent
  if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
  from config import Config
  from dbConn import MongoManager

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

    schema = {
      "type": "object",
      "properties": {
        "role": {"type": "string"},
        "skills": {"type": "array", "items": {"type": "string"}},
        "seniority_raw": {"type": "string", "enum": SENIORITY_RAW_LEVELS},
        "seniority_raw_targets": {
          "type": "array",
          "items": {"type": "string", "enum": SENIORITY_RAW_LEVELS}
        },
        "location_query": {"type": "string"},
        "location_targets": {
          "type": "array",
          "items": {"type": "string"}
        }
      },
      "required": [
        "role",
        "skills",
        "seniority_raw",
        "seniority_raw_targets",
        "location_query",
        "location_targets"
      ],
      "additionalProperties": False
    }

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
    return {
      "role": "" if is_unknown_value(llm_profile.get("role", "")) else llm_profile.get("role", ""),
      "skills": llm_profile.get("skills", []),
      "seniority_raw": "unknown" if is_unknown_value(llm_profile.get("seniority_raw", "")) else llm_profile.get("seniority_raw", "unknown"),
      "seniority_raw_targets": llm_profile.get("seniority_raw_targets", []),
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

  def _retrieve_candidates_vector(self, profile: Dict[str, Any], all_offers: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    parts = []
    role = (profile.get("role") or "").strip()
    if role and not is_unknown_value(role):
      parts.append(f"role: {role}")
    seniority = (profile.get("seniority_raw") or "").strip()
    if seniority and not is_unknown_value(seniority):
      parts.append(f"seniority: {seniority}")
    skills = profile.get("skills") or []
    if skills: parts.append(f"skills: {', '.join(skills)}")
    location_query = (profile.get("location_query") or "").strip()
    if location_query: parts.append(f"location: {location_query}")
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

  def use_case_search(self, offers: List[Dict[str, Any]], profile: Dict[str, Any], top_n: int = 10) -> Dict[str, Any]:
    if not offers:
      return {"profile": profile, "total_candidates": 0, "results": []}

    retrieval_k = getattr(Config, "RETRIEVAL_TOP_K", 50)
    top_candidates = self._retrieve_candidates_vector(profile, offers, top_k=retrieval_k)
    
    if not top_candidates:
      return {"profile": profile, "total_candidates": len(offers), "results": []}

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
      "results": results[:top_n]
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
