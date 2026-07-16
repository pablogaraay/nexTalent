from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from config import Config
from repositories.offer_repository import OfferRepository
from repositories.vector_store import VectorStore
from utils.text import normalize_text, unique_keep_order

from ..llm_client import LLMClientService


class CareerService:
  """Build an evidence-based skill gap and career plan from mapped offers."""

  OFFER_PROJECTION = {
    "_id": 0,
    "url": 1,
    "title": 1,
    "company": 1,
    "role_raw": 1,
    "seniority_raw": 1,
    "city": 1,
    "region": 1,
    "job_mapping": 1,
    "skills_sfia": 1,
    "hard_skills_raw": 1,
    "soft_skills_raw": 1,
    "tools_raw": 1,
  }
  PROFILE_SKILL_MATCH_MIN_SCORE = 0.70

  def __init__(
    self,
    llm_client_service: LLMClientService | None = None,
    vector_store: VectorStore | None = None,
    offer_repository: OfferRepository | None = None,
  ):
    self.llm_client_service = llm_client_service or LLMClientService()
    self.vector_store = vector_store or VectorStore()
    self.offer_repository = offer_repository or OfferRepository()
    self._taxonomy_skill_types: Dict[str, str] | None = None

  def _retrieve_target_offers(self, target_role: str, top_k: int) -> List[Dict[str, Any]]:
    try:
      embedding = self.llm_client_service.embed_text(f"target occupation: {target_role}")
      result = self.vector_store.query(
        collection_name=Config.OFFERS_CHROMA_COLLECTION,
        query_embedding=embedding,
        n_results=top_k,
        include=["metadatas", "distances"],
      )
      metadatas = (result.get("metadatas") or [[]])[0]
      urls = unique_keep_order([
        str((metadata or {}).get("url", "") or "").strip()
        for metadata in metadatas
        if str((metadata or {}).get("url", "") or "").strip()
      ])
      if urls:
        offers = self.offer_repository.load_mapped_offers_by_urls(
          urls,
          projection=self.OFFER_PROJECTION,
        )
        by_url = {str(offer.get("url", "")): offer for offer in offers}
        ordered = [by_url[url] for url in urls if url in by_url]
        if ordered:
          return ordered
    except Exception:
      pass

    offers = self.offer_repository.load_mapped_offers(projection=self.OFFER_PROJECTION)
    target_tokens = set(normalize_text(target_role).split())
    if not target_tokens:
      return offers[:top_k]

    scored = []
    for offer in offers:
      role_text = normalize_text(" ".join([
        str(offer.get("title", "") or ""),
        str(offer.get("role_raw", "") or ""),
      ]))
      overlap = len(target_tokens.intersection(role_text.split()))
      if overlap:
        scored.append((overlap, offer))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [offer for _, offer in scored[:top_k]]

  @staticmethod
  def _normalize_skill_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"attribute", "soft", "soft_skill"}:
      return "soft"
    if normalized in {"skill", "hard", "hard_skill"}:
      return "hard"
    return ""

  def _load_taxonomy_skill_types(self) -> Dict[str, str]:
    if self._taxonomy_skill_types is not None:
      return self._taxonomy_skill_types
    try:
      rows = self.offer_repository.load_offers(
        Config.SFIA_SKILLS_TAXONOMY_COLL,
        active_only=False,
        projection={"_id": 0, "skill_id": 1, "item_type": 1},
      )
    except Exception:
      return {}

    self._taxonomy_skill_types = {
      str(row.get("skill_id", "") or "").strip(): self._normalize_skill_type(row.get("item_type", ""))
      for row in (rows or [])
      if str(row.get("skill_id", "") or "").strip()
      and self._normalize_skill_type(row.get("item_type", ""))
    }
    return self._taxonomy_skill_types

  def _skill_type_for_offer_item(
    self,
    item: Dict[str, Any],
    offer: Dict[str, Any],
    taxonomy_types: Dict[str, str],
  ) -> str:
    direct_type = self._normalize_skill_type(item.get("item_type", ""))
    if direct_type:
      return direct_type

    skill_id = str(item.get("skill_id", "") or "").strip()
    if skill_id in taxonomy_types:
      return taxonomy_types[skill_id]
    if skill_id.startswith("SFIA_ATTR_"):
      return "soft"
    if skill_id.startswith("SFIA_SKILL_"):
      return "hard"

    raw = normalize_text(str(item.get("raw", "") or item.get("skill_name", "") or ""))
    soft_inputs = {normalize_text(str(value)) for value in (offer.get("soft_skills_raw") or [])}
    hard_inputs = {
      normalize_text(str(value))
      for value in (offer.get("hard_skills_raw") or []) + (offer.get("tools_raw") or [])
    }
    if raw and raw in soft_inputs:
      return "soft"
    if raw and raw in hard_inputs:
      return "hard"

    # SFIA professional skills are technical/professional unless marked as attributes.
    return "hard"

  def _target_skill_demand(self, offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Counter[str] = Counter()
    names: Dict[str, str] = {}
    aliases: Dict[str, set[str]] = {}
    type_counts: Dict[str, Counter[str]] = {}
    taxonomy_types = self._load_taxonomy_skill_types()

    for offer in offers:
      seen = set()
      for item in offer.get("skills_sfia", []) or []:
        skill_id = str((item or {}).get("skill_id", "") or "").strip()
        skill_name = str((item or {}).get("skill_name", "") or "").strip()
        if not skill_id or not skill_name or skill_id in seen:
          continue
        seen.add(skill_id)
        counts[skill_id] += 1
        names[skill_id] = skill_name
        skill_type = self._skill_type_for_offer_item(item or {}, offer, taxonomy_types)
        type_counts.setdefault(skill_id, Counter())[skill_type] += 1
        aliases.setdefault(skill_id, set()).update({
          normalize_text(skill_name),
          normalize_text(str((item or {}).get("raw", "") or "")),
        })

    total = len(offers)
    return [
      {
        "skill_id": skill_id,
        "skill_name": names[skill_id],
        "demand": demand,
        "share_pct": round((demand / total) * 100, 1) if total else 0.0,
        "skill_type": type_counts.get(skill_id, Counter({"hard": 1})).most_common(1)[0][0],
        "aliases": sorted(alias for alias in aliases.get(skill_id, set()) if alias),
      }
      for skill_id, demand in counts.most_common()
    ]

  def _map_profile_skills(
    self,
    profile_skills: List[str],
    target_skills: List[Dict[str, Any]],
  ) -> tuple[set[str], Dict[str, str]]:
    normalized_profile = {
      normalize_text(str(skill)): str(skill).strip()
      for skill in profile_skills
      if str(skill).strip()
    }
    covered_ids = set()
    evidence: Dict[str, str] = {}

    for target in target_skills:
      aliases = set(target.get("aliases") or [])
      aliases.add(normalize_text(target.get("skill_name", "")))
      matches = aliases.intersection(normalized_profile)
      if matches:
        matched = sorted(matches)[0]
        covered_ids.add(target["skill_id"])
        evidence[target["skill_id"]] = normalized_profile[matched]

    unresolved = [
      original
      for normalized, original in normalized_profile.items()
      if not any(normalized in set(target.get("aliases") or []) for target in target_skills)
    ]
    if not unresolved:
      return covered_ids, evidence

    try:
      collection = self.vector_store.get_collection(Config.SKILLS_CHROMA_COLLECTION)
      target_ids = {item["skill_id"] for item in target_skills}
      for skill in unresolved:
        embedding = self.llm_client_service.embed_text(f"skill: {skill}")
        result = collection.query(
          query_embeddings=[embedding],
          n_results=1,
          include=["metadatas", "distances"],
        )
        metadata = ((result.get("metadatas") or [[]])[0] or [{}])[0] or {}
        distances = (result.get("distances") or [[]])[0]
        score = 1 - float(distances[0]) if distances else 0.0
        skill_id = str(metadata.get("skill_id", "") or "").strip()
        if skill_id in target_ids and score >= self.PROFILE_SKILL_MATCH_MIN_SCORE:
          covered_ids.add(skill_id)
          evidence[skill_id] = skill
    except Exception:
      pass

    return covered_ids, evidence

  @staticmethod
  def _priority(share_pct: float) -> str:
    if share_pct >= 50:
      return "critical"
    if share_pct >= 25:
      return "recommended"
    return "complementary"

  @staticmethod
  def _readiness_label(score: int) -> str:
    if score >= 75:
      return "alta"
    if score >= 45:
      return "media"
    return "inicial"

  def _readiness_for_type(
    self,
    target_skills: List[Dict[str, Any]],
    covered_ids: set[str],
    skill_type: str,
  ) -> Dict[str, Any]:
    typed_skills = [item for item in target_skills if item.get("skill_type") == skill_type]
    total_weight = sum(item["demand"] for item in typed_skills)
    covered_weight = sum(item["demand"] for item in typed_skills if item["skill_id"] in covered_ids)
    score = round((covered_weight / total_weight) * 100) if total_weight else 0
    return {
      "score": score,
      "label": self._readiness_label(score),
      "covered_skills": sum(1 for item in typed_skills if item["skill_id"] in covered_ids),
      "target_skills": len(typed_skills),
    }

  def _build_plan_track(
    self,
    target_role: str,
    skill_type: str,
    gaps: List[Dict[str, Any]],
  ) -> Dict[str, Any]:
    phase_specs = [
      ("critical", "Fundamentos prioritarios", "Semanas 1-4"),
      ("recommended", "Capacidad aplicada", "Semanas 5-8"),
      ("complementary", "Diferenciación y portfolio", "Semanas 9-12"),
    ]
    phases = []
    for priority, title, weeks in phase_specs:
      skills = [
        gap for gap in gaps
        if gap["priority"] == priority and gap.get("skill_type") == skill_type
      ][:4]
      if not skills:
        continue
      skill_names = [skill["skill_name"] for skill in skills]
      if skill_type == "soft":
        actions = [
          f"Practicar {', '.join(skill_names)} en una situación colaborativa o simulada.",
          "Solicitar feedback concreto a una persona del equipo, mentor o compañero.",
          "Registrar una situación, la conducta aplicada y el resultado obtenido para futuras entrevistas.",
        ]
        success_evidence = (
          f"Ejemplo conductual verificable sobre {', '.join(skill_names)}, con feedback recibido "
          "y resultado documentado mediante el método situación-acción-resultado."
        )
      else:
        actions = [
          f"Estudiar los fundamentos de {', '.join(skill_names)} con práctica guiada.",
          f"Construir una evidencia aplicable a {target_role} que utilice {', '.join(skill_names)}.",
          "Documentar decisiones técnicas, resultados y aprendizajes en el portfolio o CV.",
        ]
        success_evidence = (
          f"Proyecto demostrable y explicación técnica de {', '.join(skill_names)} "
          "en un contexto similar al de las ofertas analizadas."
        )
      phases.append({
        "phase": len(phases) + 1,
        "title": title,
        "weeks": weeks,
        "skills": skill_names,
        "skill_type": skill_type,
        "actions": actions,
        "success_evidence": success_evidence,
      })

    if not phases:
      phases.append({
        "phase": 1,
        "title": "Consolidación",
        "weeks": "Semanas 1-4",
        "skills": [],
        "skill_type": skill_type,
        "actions": (
          [
            "Preparar ejemplos conductuales de las fortalezas detectadas.",
            "Solicitar feedback sobre comunicación, colaboración y autonomía.",
            "Practicar respuestas de entrevista basadas en situaciones reales.",
          ] if skill_type == "soft" else [
            f"Preparar dos casos de portfolio alineados con {target_role}.",
            "Actualizar el CV con resultados medibles y evidencias técnicas.",
            "Practicar preguntas técnicas extraídas de las ofertas objetivo.",
          ]
        ),
        "success_evidence": (
          "Tres ejemplos conductuales revisados y listos para entrevista."
          if skill_type == "soft"
          else "CV adaptado, portfolio revisado y simulación técnica completada."
        ),
      })

    return {
      "skill_type": skill_type,
      "title": "Competencias técnicas" if skill_type == "hard" else "Competencias interpersonales",
      "objective": (
        f"Construir evidencias técnicas aplicables a posiciones de {target_role}."
        if skill_type == "hard"
        else f"Desarrollar comportamientos profesionales relevantes para posiciones de {target_role}."
      ),
      "phases": phases,
    }

  def _build_plan(self, target_role: str, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    tracks = [
      self._build_plan_track(target_role, "hard", gaps),
      self._build_plan_track(target_role, "soft", gaps),
    ]
    phases = [phase for track in tracks for phase in track["phases"]]
    return {
      "duration_weeks": 12 if any(len(track["phases"]) > 1 for track in tracks) else 4,
      "objective": f"Mejorar la preparación para posiciones de {target_role} con evidencias verificables.",
      "tracks": tracks,
      "phases": phases,
      "weekly_commitment": "5-7 horas",
    }

  def use_case_career(
    self,
    profile: Dict[str, Any],
    target_role: str = "",
    offers: List[Dict[str, Any]] | None = None,
    top_k: int = 30,
  ) -> Dict[str, Any]:
    target_role = str(target_role or profile.get("role", "") or "").strip()
    if not target_role:
      raise ValueError("Debes indicar un rol objetivo para crear el plan de carrera.")

    target_offers = list(offers) if offers is not None else self._retrieve_target_offers(target_role, top_k)
    if not target_offers:
      raise ValueError(f"No hay ofertas suficientes para analizar el rol objetivo '{target_role}'.")

    target_skills = self._target_skill_demand(target_offers)
    covered_ids, evidence = self._map_profile_skills(profile.get("skills") or [], target_skills)
    hard_readiness = self._readiness_for_type(target_skills, covered_ids, "hard")
    soft_readiness = self._readiness_for_type(target_skills, covered_ids, "soft")
    total_weight = sum(item["demand"] for item in target_skills)
    covered_weight = sum(item["demand"] for item in target_skills if item["skill_id"] in covered_ids)
    score = round((covered_weight / total_weight) * 100) if total_weight else 0

    strengths = [
      {
        **{key: item[key] for key in ["skill_id", "skill_name", "skill_type", "demand", "share_pct"]},
        "profile_evidence": evidence.get(item["skill_id"], item["skill_name"]),
      }
      for item in target_skills
      if item["skill_id"] in covered_ids
    ]
    gaps = [
      {
        **{key: item[key] for key in ["skill_id", "skill_name", "skill_type", "demand", "share_pct"]},
        "priority": self._priority(float(item["share_pct"])),
        "reason": f"Aparece en el {item['share_pct']:.1f}% de las ofertas objetivo analizadas.",
      }
      for item in target_skills
      if item["skill_id"] not in covered_ids
    ]
    gaps_by_type = {
      "hard": [gap for gap in gaps if gap["skill_type"] == "hard"][:12],
      "soft": [gap for gap in gaps if gap["skill_type"] == "soft"][:12],
    }
    displayed_gaps = gaps_by_type["hard"] + gaps_by_type["soft"]
    strengths_by_type = {
      "hard": [skill for skill in strengths if skill["skill_type"] == "hard"],
      "soft": [skill for skill in strengths if skill["skill_type"] == "soft"],
    }
    offers_analyzed = len(target_offers)
    if offers_analyzed >= 20:
      confidence_label = "alta"
    elif offers_analyzed >= 10:
      confidence_label = "media"
    else:
      confidence_label = "baja"

    return {
      "profile": profile,
      "target_role": target_role,
      "readiness": {
        "score": score,
        "label": self._readiness_label(score),
        "covered_skills": len(strengths),
        "target_skills": len(target_skills),
        "by_type": {
          "hard": hard_readiness,
          "soft": soft_readiness,
        },
      },
      "market": {
        "offers_analyzed": offers_analyzed,
        "method": "demanda observada en ofertas mapeadas con SFIA",
        "confidence_label": confidence_label,
        "confidence_note": "La confianza refleja el tamaño de la muestra, no la calidad individual del candidato.",
      },
      "strengths": strengths,
      "strengths_by_type": strengths_by_type,
      "gaps": displayed_gaps,
      "gaps_by_type": gaps_by_type,
      "plan": self._build_plan(target_role, displayed_gaps),
      "sample_offers": [
        {
          "title": offer.get("title", ""),
          "company": offer.get("company", ""),
          "url": offer.get("url", ""),
        }
        for offer in target_offers[:5]
      ],
    }
