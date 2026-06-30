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
from .planner_service import PlannerService

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
      "skills": self.offer_skills(offer),
    }

  @staticmethod
  def _vector_min_score() -> float:
    return float(getattr(Config, "VECTOR_FALLBACK_MIN_SCORE", 0.60))

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

    effective_top_k = min(len(all_offers), top_k * 4) if all_offers and location_targets else top_k * 4 if location_targets else top_k

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
      return all_offers[:top_k]

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

    for offer in strong_candidates[:top_n]:
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

  def _rerank_final_with_llm(self, profile: Dict[str, Any], finalists: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
    prompt = {
      "profile": {
        "role": profile.get("role", ""),
        "skills": profile.get("skills", []),
        "seniority_raw": profile.get("seniority_raw", "unknown"),
        "seniority_raw_targets": profile.get("seniority_raw_targets", []),
        "location_query": profile.get("location_query", ""),
        "location_targets": profile.get("location_targets", []),
      },
      "instructions": {
        "objective": f"Elegir top {top_n} final.",
        "rules": [
          "Prioriza ajuste global (rol + skills + seniority).",
          "Si location_targets no está vacío, prioriza fuertemente ofertas en esas ubicaciones (city/region/country).",
          "Devuelve un JSON con campo 'ranked'.",
          f"Devuelve como maximo {top_n} elementos.",
          "Cada elemento de ranked debe incluir: offer_id (string, exact matching), score (0..1), matched_skills (array de strings).",
        ],
      },
      "offers": finalists,
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
    plan: Dict[str, Any] | None = None,
    default_plan: Dict[str, Any] | None = None,
    coerce_plan=None,
    total_candidates: int | None = None,
  ) -> Dict[str, Any]:
    total_candidates = int(total_candidates if total_candidates is not None else len(offers))
    if not offers and total_candidates <= 0:
      return {"profile": profile, "total_candidates": 0, "results": [], "agent": {}}

    active_plan = default_plan or PlannerService.default_search_plan()

    if isinstance(plan, dict) and plan and callable(coerce_plan):
      active_plan = {
        **active_plan,
        **coerce_plan(plan),
        "source": plan.get("source", "llm"),
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
      use_seniority_priority=bool(active_plan.get("use_seniority_priority", True)),
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

    if strategy_applied == "vector_only":
      vector_results = self._build_vector_only_results(top_candidates, profile, top_n)
      return {
        "profile": profile,
        "total_candidates": total_candidates,
        "results": vector_results,
        "agent": {
          "strategy_requested": strategy_requested,
          "strategy_applied": strategy_applied,
          "confidence": confidence,
          "reasons": reasons,
          "source": source,
        },
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
        results.append(
          self._build_result_entry(
            offer=offer,
            match_score=float(item.get("score", 0)),
            matched_skills=matched,
            why_match=f"Reranked by LLM. Vector Sim: {round(offer.get('vector_score', 0), 4)}",
          )
        )

    if not results:
      min_vector_score = self._vector_min_score()
      strong_candidates = [
        offer for offer in candidates_for_rerank
        if float(offer.get("vector_score", 0.0)) >= min_vector_score
      ]
      for offer in strong_candidates[:top_n]:
        results.append(
          self._build_result_entry(
            offer=offer,
            match_score=float(offer.get("vector_score", 0.0)),
            matched_skills=[],
            why_match=f"Vector Fallback Sim: {round(offer.get('vector_score', 0), 4)}",
          )
        )

    return {
      "profile": profile,
      "total_candidates": total_candidates,
      "results": results[:top_n],
      "agent": {
        "strategy_requested": strategy_requested,
        "strategy_applied": strategy_applied,
        "confidence": confidence,
        "reasons": reasons,
        "source": source,
      },
    }
