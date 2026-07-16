from __future__ import annotations

from typing import Any, Dict, List

from config import Config
from repositories.vector_store import VectorStore
from utils.text import unique_keep_order
from ..llm_client import LLMClientService
from .insights_service import InsightsService

RAW_INSIGHTS_REQUIRED_FIELDS = [
  "url",
  "title",
  "company",
  "city",
  "region",
  "country",
  "role_raw",
  "hard_skills_raw",
  "soft_skills_raw",
  "tools_raw",
  "seniority_raw",
]

ROLE_LIMIT = 0.60
SKILL_LIMIT = 0.70


class ExternalInsightsService:
  def __init__(
    self,
    llm_client_service: LLMClientService | None = None,
    vector_store: VectorStore | None = None,
    insights_service: InsightsService | None = None,
  ):
    self.llm_client_service = llm_client_service or LLMClientService()
    self.vector_store = vector_store or VectorStore()
    self.insights_service = insights_service or InsightsService()

  def _best_match(self, collection, text: str, limit: float) -> Dict[str, Any]:
    text = str(text or "").strip()
    if not text:
      return {"status": "unmapped", "top1": None}

    embedding = self.llm_client_service.embed_text(text)
    result = collection.query(
      query_embeddings=[embedding],
      n_results=3,
      include=["metadatas", "distances"],
    )
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    candidates = []
    for metadata, distance in zip(metadatas, distances):
      candidates.append({"metadata": metadata or {}, "score": 1 - float(distance)})

    if not candidates:
      return {"status": "unmapped", "top1": None}

    top1 = candidates[0]
    if top1["score"] >= limit:
      return {"status": "mapped", "top1": top1}
    return {"status": "unmapped", "top1": top1}

  @staticmethod
  def _clean_skill_inputs(offer: Dict[str, Any]) -> List[str]:
    skill_inputs: List[str] = []
    for field in ["hard_skills_raw", "soft_skills_raw", "tools_raw"]:
      values = offer.get(field, []) or []
      if isinstance(values, str):
        values = [values]
      skill_inputs.extend([str(item) for item in values])
    return unique_keep_order(skill_inputs)

  @staticmethod
  def _validate_raw_offers(raw_offers: Any) -> tuple[List[Dict[str, Any]], List[str]]:
    if not isinstance(raw_offers, list):
      raise ValueError("El JSON debe ser un array de ofertas.")

    clean_offers: List[Dict[str, Any]] = []
    warnings: List[str] = []
    missing_by_field = {field: 0 for field in RAW_INSIGHTS_REQUIRED_FIELDS}
    skipped = 0

    for offer in raw_offers:
      if not isinstance(offer, dict):
        skipped += 1
        continue

      for field in RAW_INSIGHTS_REQUIRED_FIELDS:
        value = offer.get(field)
        if value is None or value == "":
          missing_by_field[field] += 1

      clean_offer = dict(offer)
      clean_offer["is_active"] = bool(clean_offer.get("is_active", True))
      clean_offers.append(clean_offer)

    if skipped:
      warnings.append(f"{skipped} elementos se ignoraron porque no eran objetos JSON.")

    for field, count in missing_by_field.items():
      if count:
        warnings.append(f"{count} ofertas no incluyen '{field}' o lo tienen vacío.")

    if not clean_offers:
      raise ValueError("El JSON no contiene ofertas válidas.")

    return clean_offers, warnings

  def map_raw_offers(self, raw_offers: Any) -> tuple[List[Dict[str, Any]], List[str]]:
    offers, warnings = self._validate_raw_offers(raw_offers)
    active_offers = [offer for offer in offers if offer.get("is_active", True) is not False]
    if not active_offers:
      raise ValueError("El JSON no contiene ofertas activas.")

    jobs_collection = self.vector_store.get_collection(Config.JOBS_CHROMA_COLLECTION)
    skills_collection = self.vector_store.get_collection(Config.SKILLS_CHROMA_COLLECTION)

    mapped_offers: List[Dict[str, Any]] = []
    unmapped_roles = 0
    offers_without_mapped_skills = 0

    for offer in active_offers:
      mapped_offer = dict(offer)
      mapped_offer["job_mapping"] = {}
      mapped_offer["skills_sfia"] = []

      role_match = self._best_match(jobs_collection, mapped_offer.get("role_raw", ""), ROLE_LIMIT)
      if role_match["status"] == "mapped" and role_match["top1"]:
        metadata = role_match["top1"]["metadata"] or {}
        mapped_offer["job_mapping"] = {
          "job_id_wef": metadata.get("job_id", ""),
          "job_family_wef": metadata.get("job_family", ""),
          "score": role_match["top1"]["score"],
        }
      else:
        unmapped_roles += 1

      skills_mapped = []
      for skill in self._clean_skill_inputs(mapped_offer):
        skill_match = self._best_match(skills_collection, skill, SKILL_LIMIT)
        if skill_match["status"] != "mapped" or not skill_match["top1"]:
          continue

        metadata = skill_match["top1"]["metadata"] or {}
        skills_mapped.append({
          "skill_id": metadata.get("skill_id", ""),
          "skill_name": metadata.get("skill_name", ""),
          "item_type": metadata.get("item_type", ""),
          "score": skill_match["top1"]["score"],
          "raw": skill,
        })

      mapped_offer["skills_sfia"] = skills_mapped
      if not skills_mapped:
        offers_without_mapped_skills += 1

      mapped_offers.append(mapped_offer)

    if unmapped_roles:
      warnings.append(f"{unmapped_roles} ofertas no pudieron mapearse a la taxonomía de perfiles.")
    if offers_without_mapped_skills:
      warnings.append(f"{offers_without_mapped_skills} ofertas no tuvieron habilidades mapeadas.")

    return mapped_offers, warnings

  def use_case_insights_from_raw_json(
    self,
    raw_offers: Any,
    top_n: int = 10,
    filters: Dict[str, str] | None = None,
  ) -> Dict[str, Any]:
    mapped_offers, warnings = self.map_raw_offers(raw_offers)
    result = self.insights_service.use_case_insights(
      mapped_offers,
      top_n=top_n,
      filters=filters or {},
    )
    result["source"] = "uploaded_raw_json"
    result["warnings"] = warnings
    result["required_fields"] = RAW_INSIGHTS_REQUIRED_FIELDS
    return result
