from __future__ import annotations

import json
from typing import Any, Dict

from config import Config
from utils.text import unique_keep_order

from ..llm_client import LLMClientService


class PlannerService:
  def __init__(self, llm_client_service: LLMClientService | None = None):
    self.llm_client_service = llm_client_service or LLMClientService()

  @staticmethod
  def default_search_plan() -> Dict[str, Any]:
    return {
      "strategy": "llm_rerank",
      "confidence": 0.5,
      "reasons": ["default_plan"],
      "use_location_priority": True,
      "use_seniority_priority": True,
      "top_k_hint": int(getattr(Config, "RETRIEVAL_TOP_K", 50)),
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
      "location_targets": profile.get("location_targets", []),
    }
    user_prompt = (
      "Analiza el siguiente perfil y selecciona una herramienta para decidir la estrategia de búsqueda.\n\n"
      f"{json.dumps(profile_payload, ensure_ascii=False, indent=2)}"
    )
    return system_prompt, user_prompt

  def _coerce_search_plan(self, raw_plan: Dict[str, Any]) -> Dict[str, Any]:
    plan = self.default_search_plan()
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

  def coerce_search_plan(self, raw_plan: Dict[str, Any]) -> Dict[str, Any]:
    return self._coerce_search_plan(raw_plan)

  def decide_search_plan(self, profile: Dict[str, Any]) -> Dict[str, Any]:
    base_plan = self.default_search_plan()
    try:
      system_prompt, user_prompt = self._build_autonomous_planner_prompts(profile or {})
      tool_result = self.llm_client_service.call_autonomous_strategy_tool(system_prompt, user_prompt)
      tool_name = str((tool_result or {}).get("tool_name", "") or "").strip()
      raw_args = (tool_result or {}).get("arguments", {}) or {}

      strategy_map = {
        "run_llm_rerank": "llm_rerank",
        "run_vector_only": "vector_only",
        "run_no_match": "no_match",
      }

      if tool_name in strategy_map:
        raw_plan = {
          **raw_args,
          "strategy": strategy_map[tool_name],
        }
        source = "llm_tool_calling"
      else:
        raw_plan = base_plan
        source = "default_plan_no_tool_call"

      plan = self._coerce_search_plan(raw_plan)
      return {
        **plan,
        "source": source,
      }
    except Exception as exc:
      if getattr(Config, "AUTONOMOUS_AGENT_VERBOSE", False):
        print(f"Autonomous planner fallback to default plan: {exc}")
      return {**base_plan, "source": "fallback_default"}
