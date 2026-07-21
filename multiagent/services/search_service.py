from __future__ import annotations
from typing import Any, Dict, Iterable, List
from config import Config
from repositories.offer_repository import OfferRepository
from repositories.vector_store import VectorStore
from utils.text import (
  is_unknown_value,
  normalize_text,
  offer_location_string,
  unique_keep_order,
)
from ..llm_client import LLMClientService

class SearchService:
  SEARCH_OFFER_PROJECTION = {
    "_id": 0,
    "url": 1,
    "title": 1,
    "company": 1,
    "role_raw": 1,
    "seniority_raw": 1,
    "city": 1,
    "region": 1,
    "country": 1,
    "job_mapping": 1,
    "skills_sfia": 1,
    "technologies_onet": 1,
    "hard_skills_raw": 1,
    "soft_skills_raw": 1,
    "tools_raw": 1,
  }

  def __init__(
    self,
    llm_client_service: LLMClientService | None = None,
    vector_store: VectorStore | None = None,
    offer_repository: OfferRepository | None = None,
  ):
    self.llm_client_service = llm_client_service or LLMClientService()
    self.vector_store = vector_store or VectorStore()
    self.offer_repository = offer_repository or OfferRepository()

  @staticmethod
  def offer_skills(offer: Dict[str, Any]) -> List[str]:
    raw: List[str] = []
    raw.extend(offer.get("hard_skills_raw", []) or [])
    raw.extend(offer.get("soft_skills_raw", []) or [])
    raw.extend(offer.get("tools_raw", []) or [])
    raw.extend([(item or {}).get("skill_name", "") for item in (offer.get("skills_sfia", []) or [])])
    raw.extend([
      (item or {}).get("preferred_label", "")
      for item in (offer.get("technologies_onet", []) or [])
    ])
    return unique_keep_order([str(item) for item in raw])[:12]

  @staticmethod
  def _vector_min_score() -> float:
    return float(getattr(Config, "VECTOR_FALLBACK_MIN_SCORE", 0.60))

  @staticmethod
  def default_search_plan() -> Dict[str, Any]:
    return {
      "strategy": "vector_only",
      "confidence": 0.5,
      "reasons": ["default_plan"],
      "use_location_priority": True,
      "use_seniority_priority": True,
      "top_k_hint": int(getattr(Config, "RETRIEVAL_TOP_K", 50)),
      "source": "default_plan",
    }

  def _build_result_entry(
    self,
    offer: Dict[str, Any],
    match_score: float,
    matched_skills: List[str] | None,
    why_match: str,
  ) -> Dict[str, Any]:
    return {
      "url": offer.get("url", ""),
      "title": offer.get("title", ""),
      "company": offer.get("company", ""),
      "role_raw": offer.get("role_raw", ""),
      "location": offer_location_string(offer),
      "job_mapping": offer.get("job_mapping", {}),
      "match_score": round(float(match_score), 4),
      "matched_skills": unique_keep_order([str(s) for s in (matched_skills or [])]),
      "why_match": why_match,
      "vector_score": round(float(offer.get("vector_score", 0.0)), 4),
    }

  def _build_search_query(
    self,
    profile: Dict[str, Any],
    use_location_priority: bool,
    use_seniority_priority: bool,
  ) -> str:
    parts = []
    role = (profile.get("role") or "").strip()
    if role and not is_unknown_value(role):
      parts.append(f"role: {role}")

    role_candidates = [str(x).strip() for x in (profile.get("role_candidates") or []) if str(x).strip()]
    if role_candidates:
      parts.append(f"related_roles: {', '.join(role_candidates[:3])}")

    performed_roles = [str(x).strip() for x in (profile.get("performed_roles") or []) if str(x).strip()]
    if performed_roles:
      parts.append(f"performed_roles: {', '.join(performed_roles[:6])}")

    normalized_roles = [
      str((item or {}).get("occupation", "") or "").strip()
      for item in (profile.get("normalized_roles") or [])
      if str((item or {}).get("occupation", "") or "").strip()
    ]
    if normalized_roles:
      parts.append(f"normalized_roles: {', '.join(normalized_roles[:6])}")

    role_experiences = []
    for item in (profile.get("role_experiences") or [])[:6]:
      role = str((item or {}).get("role", "") or "").strip()
      normalized = str((item or {}).get("normalized_occupation", "") or "").strip()
      seniority_item = str((item or {}).get("seniority_raw", "") or "").strip()
      if role:
        role_experiences.append(" / ".join([value for value in [role, normalized, seniority_item] if value]))
    if role_experiences:
      parts.append(f"role_experience_analysis: {'; '.join(role_experiences)}")

    seniority = (profile.get("seniority_raw") or "").strip()
    if use_seniority_priority and seniority and not is_unknown_value(seniority):
      parts.append(f"seniority: {seniority}")

    skills = profile.get("skills") or []
    if skills:
      parts.append(f"skills: {', '.join(skills)}")

    location_query = (profile.get("location_query") or "").strip()
    if use_location_priority and location_query:
      parts.append(f"location: {location_query}")

    return " | ".join(parts) if parts else ""

  def _hydrate_offers_from_results(
    self,
    all_offers: List[Dict[str, Any]],
    metas: Iterable[Dict[str, Any]],
    dists: Iterable[float],
  ) -> List[Dict[str, Any]]:
    offers_by_url = {offer.get("url"): offer for offer in all_offers}
    retrieved = []
    for m, d in zip(metas, dists):
      url = (m or {}).get("url")
      if url and url in offers_by_url:
        offer = dict(offers_by_url[url])
        offer["vector_score"] = 1.0 - d
        retrieved.append(offer)
    return retrieved

  def _hydrate_offers_by_urls(
    self,
    metas: Iterable[Dict[str, Any]],
    dists: Iterable[float],
  ) -> List[Dict[str, Any]]:
    hits = []
    urls = []
    seen_urls = set()
    for m, d in zip(metas, dists):
      url = (m or {}).get("url")
      if not url:
        continue
      hits.append((url, d))
      if url not in seen_urls:
        urls.append(url)
        seen_urls.add(url)

    offers = self.offer_repository.load_mapped_offers_by_urls(
      urls,
      projection=self.SEARCH_OFFER_PROJECTION,
    )
    offers_by_url = {offer.get("url"): offer for offer in offers}

    retrieved = []
    for url, d in hits:
      if url in offers_by_url:
        offer = dict(offers_by_url[url])
        offer["vector_score"] = 1.0 - d
        retrieved.append(offer)
    return retrieved

  @staticmethod
  def _apply_location_priority(retrieved: List[Dict[str, Any]], location_targets: List[str]) -> List[Dict[str, Any]]:
    if not location_targets:
      return retrieved

    location_filtered = []
    for offer in retrieved:
      loc = normalize_text(offer_location_string(offer))
      if any(target in loc for target in location_targets):
        location_filtered.append(offer)

    if not location_filtered:
      return retrieved

    remainder = [offer for offer in retrieved if offer not in location_filtered]
    return location_filtered + remainder

  def _retrieve_candidates_vector(
    self,
    profile: Dict[str, Any],
    all_offers: List[Dict[str, Any]],
    top_k: int,
    use_location_priority: bool = True,
    use_seniority_priority: bool = True,
    return_all: bool = False,
  ) -> List[Dict[str, Any]]:
    query_text = self._build_search_query(profile, use_location_priority, use_seniority_priority)
    if not query_text:
      return []

    qv = self.llm_client_service.embed_text(query_text)
    location_targets = []
    if use_location_priority:
      location_targets = [
        normalize_text(str(x))
        for x in (profile.get("location_targets") or [])
        if str(x).strip()
      ]

    if return_all:
      effective_top_k = top_k
    elif all_offers and location_targets:
      effective_top_k = min(len(all_offers), top_k * 4)
    elif location_targets:
      effective_top_k = top_k * 4
    else:
      effective_top_k = top_k

    try:
      res = self.vector_store.query(
        collection_name=Config.OFFERS_CHROMA_COLLECTION,
        query_embedding=qv,
        n_results=effective_top_k,
        include=["metadatas", "distances"],
      )
    except Exception:
      print("No se encontro la coleccion en ChromaDB. Regresando lista truncada.")
      if not all_offers:
        all_offers = self.offer_repository.load_mapped_offers(projection=self.SEARCH_OFFER_PROJECTION)
      return all_offers if return_all else all_offers[:top_k]

    metas = res.get("metadatas", [[]])[0] if res.get("metadatas") else []
    dists = res.get("distances", [[]])[0] if res.get("distances") else []

    if all_offers:
      retrieved = self._hydrate_offers_from_results(all_offers, metas, dists)
    else:
      retrieved = self._hydrate_offers_by_urls(metas, dists)
    retrieved = self._apply_location_priority(retrieved, location_targets)
    return retrieved

  def _build_vector_only_results(
    self,
    top_candidates: List[Dict[str, Any]],
    profile: Dict[str, Any],
    top_n: int,
  ) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    profile_skills = {normalize_text(str(s)) for s in (profile.get("skills") or [])}
    min_vector_score = self._vector_min_score()
    strong_candidates = [offer for offer in top_candidates if float(offer.get("vector_score", 0.0)) >= min_vector_score]

    selected_candidates = strong_candidates if top_n <= 0 else strong_candidates[:top_n]

    for offer in selected_candidates:
      offer_skills = [str(x) for x in self.offer_skills(offer)]
      matched = [s for s in offer_skills if normalize_text(s) in profile_skills]
      out.append(
        self._build_result_entry(
          offer=offer,
          match_score=float(offer.get("vector_score", 0.0)),
          matched_skills=matched,
          why_match="Coincidencia semántica por embeddings",
        )
      )
    return out

  def use_case_search(
    self,
    offers: List[Dict[str, Any]],
    profile: Dict[str, Any],
    top_n: int = 10,
    plan: Dict[str, Any] | None = None,
    default_plan: Dict[str, Any] | None = None,
    coerce_plan=None,
    total_candidates: int | None = None,
  ) -> Dict[str, Any]:
    total_candidates = int(total_candidates if total_candidates is not None else len(offers))
    result_limit = int(top_n or 0)
    return_all_matches = result_limit <= 0
    if not offers and total_candidates <= 0:
      return {"profile": profile, "total_candidates": 0, "results": [], "agent": {}}

    active_plan = default_plan or self.default_search_plan()

    if isinstance(plan, dict) and plan:
      plan_payload = coerce_plan(plan) if callable(coerce_plan) else plan
      active_plan = {
        **active_plan,
        **plan_payload,
        "source": plan.get("source", plan_payload.get("source", "rules")),
      }

    strategy_requested = str(active_plan.get("strategy", "vector_only") or "vector_only").strip()
    strategy_applied = "no_match" if strategy_requested == "no_match" else "vector_only"
    confidence = round(float(active_plan.get("confidence", 0.0)), 4)
    reasons = active_plan.get("reasons", [])
    source = active_plan.get("source", "")

    if strategy_applied == "no_match":
      return {
        "profile": profile,
        "total_candidates": total_candidates,
        "results": [],
        "agent": {
          "strategy_requested": strategy_requested,
          "strategy_applied": strategy_applied,
          "confidence": confidence,
          "reasons": reasons,
          "source": source,
          "message": "No hay señal suficiente para recomendar ofertas con calidad.",
        },
      }

    retrieval_k_default = int(getattr(Config, "RETRIEVAL_TOP_K", 50))
    retrieval_k = (
      total_candidates
      if return_all_matches
      else max(result_limit, min(200, int(active_plan.get("top_k_hint", retrieval_k_default))))
    )

    top_candidates = self._retrieve_candidates_vector(
      profile,
      offers,
      top_k=retrieval_k,
      use_location_priority=bool(active_plan.get("use_location_priority", True)),
      use_seniority_priority=bool(active_plan.get("use_seniority_priority", True)),
      return_all=return_all_matches,
    )

    if not top_candidates:
      return {
        "profile": profile,
        "total_candidates": total_candidates,
        "results": [],
        "agent": {
          "strategy_requested": strategy_requested,
          "strategy_applied": strategy_applied,
          "confidence": confidence,
          "reasons": reasons,
          "source": source,
        },
      }

    results = self._build_vector_only_results(top_candidates, profile, top_n)
    return {
      "profile": profile,
      "total_candidates": total_candidates,
      "results": results,
      "agent": {
        "strategy_requested": strategy_requested,
        "strategy_applied": strategy_applied,
        "confidence": confidence,
        "reasons": reasons,
        "source": source,
      },
    }
