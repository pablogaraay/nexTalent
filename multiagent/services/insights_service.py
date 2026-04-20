from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from config import Config


class InsightsService:
  def __init__(self):
    self._job_title_map: Dict[str, str] | None = None

  @staticmethod
  def _safe_share(count: int, total: int) -> float:
    if total <= 0:
      return 0.0
    return round((count / total) * 100.0, 2)

  def _load_job_title_map(self) -> Dict[str, str]:
    if self._job_title_map is not None:
      return self._job_title_map

    base_dir = Path(__file__).resolve().parent.parent.parent
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

  def use_case_insights(self, offers: List[Dict], top_n: int = 10) -> Dict:
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

    return {
      "generated_at_utc": datetime.now(timezone.utc).isoformat(),
      "collection": Config.MAPPED_COLL,
      "summary": {
        "total_offers": total_offers,
        "offers_with_job_mapping": offers_with_job_mapping,
        "offers_with_skills_sfia": offers_with_skills_sfia,
        "job_mapping_coverage_pct": self._safe_share(offers_with_job_mapping, total_offers),
        "skills_sfia_coverage_pct": self._safe_share(offers_with_skills_sfia, total_offers),
      },
      "top_jobs": top_jobs,
      "top_skills": top_skills,
    }
