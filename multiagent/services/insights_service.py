from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from config import Config
from repositories.offer_repository import OfferRepository


class InsightsService:
  def __init__(self, taxonomy_repository: OfferRepository | None = None):
    self._job_title_map: Dict[str, str] | None = None
    self.taxonomy_repository = taxonomy_repository

  @staticmethod
  def _safe_share(count: int, total: int) -> float:
    if total <= 0:
      return 0.0
    return round((count / total) * 100.0, 2)

  def _load_job_title_map(self) -> Dict[str, str]:
    if self._job_title_map is not None:
      return self._job_title_map

    out: Dict[str, str] = {}
    repository = self.taxonomy_repository
    should_close_repository = False

    try:
      if repository is None:
        repository = OfferRepository()
        should_close_repository = True

      rows = repository.load_offers(
        Config.WEF_JOBS_TAXONOMY_COLL,
        active_only=False,
        projection={"_id": 0, "job_id": 1, "occupation": 1, "active": 1},
      )
      if isinstance(rows, list):
        for row in rows:
          if (row or {}).get("active", True) is False:
            continue
          job_id = str((row or {}).get("job_id", "")).strip()
          title = str((row or {}).get("occupation", "")).strip()
          if job_id and title:
            out[job_id] = title
    except Exception:
      out = {}
    finally:
      if should_close_repository and repository is not None:
        repository.close()

    self._job_title_map = out
    return out

  @staticmethod
  def _normalize(value: str) -> str:
    return str(value or "").strip().lower()

  def _offer_matches_filters(self, offer: Dict, filters: Dict[str, str]) -> bool:
    company = str(offer.get("company", "") or "").strip()
    city = str(offer.get("city", "") or "").strip()
    region = str(offer.get("region", "") or "").strip()
    seniority = str(offer.get("seniority_raw", "") or "").strip()
    job_family = str(((offer.get("job_mapping") or {}).get("job_family_wef", "") or "")).strip()

    checks = [
      ("company", company),
      ("city", city),
      ("region", region),
      ("seniority", seniority),
      ("job_family", job_family),
    ]
    for key, offer_value in checks:
      selected_value = self._normalize(filters.get(key, ""))
      if selected_value and self._normalize(offer_value) != selected_value:
        return False
    return True

  @staticmethod
  def _count_values(offers: List[Dict], getter) -> List[Dict[str, int | str]]:
    counts: Dict[str, int] = {}
    for offer in offers:
      value = str(getter(offer) or "").strip()
      if not value:
        continue
      counts[value] = counts.get(value, 0) + 1
    return [
      {"value": value, "count": count}
      for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    ]

  def use_case_insights(self, offers: List[Dict], top_n: int = 10, filters: Dict[str, str] | None = None) -> Dict:
    top_n = max(1, min(int(top_n), 100))
    filters = filters or {}
    base_offers = offers or []
    filtered_offers = [offer for offer in base_offers if self._offer_matches_filters(offer, filters)]
    total_offers = len(filtered_offers)
    job_title_map = self._load_job_title_map()

    offers_with_job_mapping = 0
    offers_with_skills_sfia = 0
    offers_with_technologies_onet = 0

    jobs_counter: Dict[tuple, int] = {}
    skills_counter: Dict[tuple, int] = {}
    technologies_counter: Dict[tuple, int] = {}

    for offer in filtered_offers:
      job_id = str(((offer.get("job_mapping") or {}).get("job_id_wef", "") or "")).strip()
      job_family = str(((offer.get("job_mapping") or {}).get("job_family_wef", "") or "")).strip()
      if job_id:
        offers_with_job_mapping += 1
        key = (job_id, job_family)
        jobs_counter[key] = jobs_counter.get(key, 0) + 1

      skills = offer.get("skills_sfia") or []
      if skills:
        offers_with_skills_sfia += 1

      seen_skill_ids = set()
      for item in skills:
        skill_id = str(((item or {}).get("skill_id", "") or "")).strip()
        skill_name = str(((item or {}).get("skill_name", "") or "")).strip()
        if not skill_id or skill_id in seen_skill_ids:
          continue
        seen_skill_ids.add(skill_id)
        key = (skill_id, skill_name)
        skills_counter[key] = skills_counter.get(key, 0) + 1

      technologies = offer.get("technologies_onet") or []
      if technologies:
        offers_with_technologies_onet += 1
      seen_technology_ids = set()
      for item in technologies:
        technology_id = str(((item or {}).get("technology_id", "") or "")).strip()
        preferred_label = str(((item or {}).get("preferred_label", "") or "")).strip()
        category_id = str(((item or {}).get("category_id", "") or "")).strip()
        if not technology_id or not preferred_label or technology_id in seen_technology_ids:
          continue
        seen_technology_ids.add(technology_id)
        key = (technology_id, preferred_label, category_id)
        technologies_counter[key] = technologies_counter.get(key, 0) + 1

    top_jobs = []
    for (job_id, job_family), demand in sorted(jobs_counter.items(), key=lambda x: x[1], reverse=True)[:top_n]:
      job_title = job_title_map.get(job_id, "")
      top_jobs.append({
        "job_id": job_id,
        "job_title": job_title if job_title else job_id,
        "job_family": job_family,
        "demand": demand,
        "share_total_offers_pct": self._safe_share(demand, total_offers),
      })

    top_skills = []
    for (skill_id, skill_name), demand in sorted(skills_counter.items(), key=lambda x: x[1], reverse=True)[:top_n]:
      top_skills.append({
        "skill_id": skill_id,
        "skill_name": skill_name,
        "demand": demand,
        "share_total_offers_pct": self._safe_share(demand, total_offers),
      })

    top_technologies = []
    for (technology_id, preferred_label, category_id), demand in sorted(
      technologies_counter.items(), key=lambda x: x[1], reverse=True
    )[:top_n]:
      top_technologies.append({
        "technology_id": technology_id,
        "preferred_label": preferred_label,
        "category_id": category_id,
        "demand": demand,
        "share_total_offers_pct": self._safe_share(demand, total_offers),
      })

    return {
      "generated_at_utc": datetime.now(timezone.utc).isoformat(),
      "collection": Config.MAPPED_COLL,
      "applied_filters": {
        "company": str(filters.get("company", "") or "").strip(),
        "city": str(filters.get("city", "") or "").strip(),
        "region": str(filters.get("region", "") or "").strip(),
        "seniority": str(filters.get("seniority", "") or "").strip(),
        "job_family": str(filters.get("job_family", "") or "").strip(),
      },
      "available_filters": {
        "companies": self._count_values(base_offers, lambda offer: offer.get("company", "")),
        "cities": self._count_values(base_offers, lambda offer: offer.get("city", "")),
        "regions": self._count_values(base_offers, lambda offer: offer.get("region", "")),
        "seniorities": self._count_values(base_offers, lambda offer: offer.get("seniority_raw", "")),
        "job_families": self._count_values(base_offers, lambda offer: (offer.get("job_mapping") or {}).get("job_family_wef", "")),
      },
      "summary": {
        "total_offers": len(base_offers),
        "filtered_offers": total_offers,
        "offers_with_job_mapping": offers_with_job_mapping,
        "offers_with_skills_sfia": offers_with_skills_sfia,
        "offers_with_technologies_onet": offers_with_technologies_onet,
        "job_mapping_coverage_pct": self._safe_share(offers_with_job_mapping, total_offers),
        "skills_sfia_coverage_pct": self._safe_share(offers_with_skills_sfia, total_offers),
        "technologies_onet_coverage_pct": self._safe_share(offers_with_technologies_onet, total_offers),
      },
      "top_jobs": top_jobs,
      "top_skills": top_skills,
      "top_technologies": top_technologies,
    }
