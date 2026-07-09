from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from config import Config
from repositories.offer_repository import OfferRepository
from utils.text import is_unknown_value

from .llm_client import LLMClientService
from .services.insights_service import InsightsService
from .services.profile_service import ProfileService
from .services.search_service import SearchService


class GraphState(TypedDict, total=False):
  params: Dict[str, Any]
  offers: List[Dict[str, Any]]
  total_candidates: int
  profile: Dict[str, Any]
  profile_signal: Dict[str, Any]
  profile_enrichment_attempted: bool
  plan: Dict[str, Any]
  result: Dict[str, Any]
  error: str
  use_case: str


_COMPILED_GRAPH = None


def _parse_top_n_param(params: Dict[str, Any], default: int = 10) -> int:
  raw_value = (params or {}).get("top_n", default)
  if raw_value is None or raw_value == "":
    return default
  return int(raw_value)


def build_multiagent_graph():
  llm_client_service = LLMClientService()
  offer_repository = OfferRepository()
  profile_service = ProfileService(llm_client_service)
  search_service = SearchService(llm_client_service, offer_repository=offer_repository)
  insights_service = InsightsService()
  graph = StateGraph(GraphState)

  insights_projection = {
    "_id": 0,
    "company": 1,
    "city": 1,
    "region": 1,
    "seniority_raw": 1,
    "job_mapping": 1,
    "skills_sfia": 1,
    "is_active": 1,
  }

  def load_data_node(state: GraphState) -> GraphState:
    try:
      params = state.get("params", {}) or {}
      use_case = str(params.get("use_case", "search") or "search").strip().lower()
      if use_case == "insights":
        offers = offer_repository.load_mapped_offers(projection=insights_projection) or []
        if not offers:
          return {
            **state,
            "offers": [],
            "use_case": use_case,
            "error": f"No hay ofertas disponibles en la coleccion '{Config.MAPPED_COLL}'.",
          }
        return {**state, "offers": offers, "use_case": use_case, "total_candidates": len(offers)}

      total_candidates = offer_repository.count_mapped_offers()
      if total_candidates <= 0:
        return {
          **state,
          "offers": [],
          "use_case": use_case,
          "error": f"No hay ofertas disponibles en la coleccion '{Config.MAPPED_COLL}'.",
        }
      return {**state, "offers": [], "use_case": use_case, "total_candidates": total_candidates}
    except Exception as exc:
      return {**state, "offers": [], "error": f"Error cargando datos desde Mongo: {exc}"}

  def route_after_load(state: GraphState) -> str:
    if state.get("error"):
      return "end"
    use_case = str(state.get("use_case", "search") or "search").strip().lower()
    if use_case == "insights":
      return "insights"
    return "search"

  def parse_profile_node(state: GraphState) -> GraphState:
    if state.get("error"):
      return state
    params = state.get("params", {}) or {}
    try:
      profile = profile_service.parse_profile(
        profile_text=params.get("profile_text", "") or "",
        cv_file=params.get("cv_file", "") or "",
      )
      return {
        **state,
        "profile": profile,
        "profile_enrichment_attempted": False,
      }
    except Exception as exc:
      return {
        **state,
        "error": f"Error parseando perfil con LLM: {exc}",
      }

  def assess_profile_signal_node(state: GraphState) -> GraphState:
    if state.get("error"):
      return state
    try:
      signal = profile_service.assess_profile_signal(state.get("profile", {}) or {})
      return {**state, "profile_signal": signal}
    except Exception as exc:
      return {
        **state,
        "error": f"Error evaluando perfil: {exc}",
      }

  def route_after_profile_assessment(state: GraphState) -> str:
    if state.get("error"):
      return "end"
    signal = state.get("profile_signal", {}) or {}
    level = str(signal.get("level", "weak") or "weak").strip().lower()
    enrichment_attempted = bool(state.get("profile_enrichment_attempted", False))
    if level == "strong":
      return "search"
    if not enrichment_attempted:
      return "enrich_profile"
    return "search"

  def enrich_profile_node(state: GraphState) -> GraphState:
    if state.get("error"):
      return state
    try:
      enriched = profile_service.enrich_profile(state.get("profile", {}) or {})
      return {
        **state,
        "profile": enriched,
        "profile_enrichment_attempted": True,
      }
    except Exception as exc:
      if getattr(Config, "AUTONOMOUS_AGENT_VERBOSE", False):
        print(f"Profile enrichment fallback to original profile: {exc}")
      return {
        **state,
        "profile_enrichment_attempted": True,
      }

  def build_search_plan(profile: Dict[str, Any], signal: Dict[str, Any]) -> Dict[str, Any]:
    level = str(signal.get("level", "weak") or "weak").strip().lower()
    reasons = [str(reason) for reason in (signal.get("reasons") or [])]
    score = round(float(signal.get("score", 0.0) or 0.0), 4)
    missing_role_and_skills = "falta_rol_claro" in reasons and "falta_skills" in reasons

    if level in {"strong", "medium"} or not missing_role_and_skills:
      strategy = "vector_only"
    else:
      strategy = "no_match"

    return {
      "strategy": strategy,
      "confidence": score,
      "reasons": reasons or [f"profile_signal_{level}"],
      "use_location_priority": bool(
        str(profile.get("location_query", "") or "").strip()
        or [x for x in (profile.get("location_targets") or []) if str(x).strip()]
      ),
      "use_seniority_priority": bool(
        not is_unknown_value(str(profile.get("seniority_raw", "unknown") or "unknown"))
      ),
      "top_k_hint": int(getattr(Config, "RETRIEVAL_TOP_K", 50)),
      "source": "profile_signal_rules",
    }

  def search_node(state: GraphState) -> GraphState:
    if state.get("error"):
      return state
    try:
      params = state.get("params", {}) or {}
      top_n = _parse_top_n_param(params)
      plan = build_search_plan(
        state.get("profile", {}) or {},
        state.get("profile_signal", {}) or {},
      )
      result = search_service.use_case_search(
        state.get("offers", []),
        state.get("profile", {}),
        top_n=top_n,
        plan=plan,
        total_candidates=state.get("total_candidates"),
      )
      return {**state, "plan": plan, "result": result}
    except Exception as exc:
      return {
        **state,
        "error": f"Error en ranking LLM: {exc}",
      }

  def insights_node(state: GraphState) -> GraphState:
    if state.get("error"):
      return state
    try:
      params = state.get("params", {}) or {}
      top_n = _parse_top_n_param(params)
      result = insights_service.use_case_insights(
        state.get("offers", []),
        top_n=top_n,
        filters={
          "company": str(params.get("company", "") or "").strip(),
          "city": str(params.get("city", "") or "").strip(),
          "region": str(params.get("region", "") or "").strip(),
          "seniority": str(params.get("seniority", "") or "").strip(),
          "job_family": str(params.get("job_family", "") or "").strip(),
        },
      )
      return {**state, "result": result}
    except Exception as exc:
      return {
        **state,
        "error": f"Error generando insights de mercado: {exc}",
      }

  graph.add_node("load_data", load_data_node)
  graph.add_node("parse_profile", parse_profile_node)
  graph.add_node("assess_profile_signal", assess_profile_signal_node)
  graph.add_node("enrich_profile", enrich_profile_node)
  graph.add_node("search", search_node)
  graph.add_node("insights", insights_node)

  graph.set_entry_point("load_data")
  graph.add_conditional_edges(
    "load_data",
    route_after_load,
    {
      "search": "parse_profile",
      "insights": "insights",
      "end": END,
    },
  )
  graph.add_edge("parse_profile", "assess_profile_signal")
  graph.add_conditional_edges(
    "assess_profile_signal",
    route_after_profile_assessment,
	  {
	    "search": "search",
	    "enrich_profile": "enrich_profile",
	    "end": END,
	  },
	)
  graph.add_edge("enrich_profile", "assess_profile_signal")
  graph.add_edge("search", END)
  graph.add_edge("insights", END)

  return graph.compile()


def get_multiagent_graph():
  global _COMPILED_GRAPH
  if _COMPILED_GRAPH is None:
    _COMPILED_GRAPH = build_multiagent_graph()
  return _COMPILED_GRAPH


def run_multiagent_flow(params: Dict[str, Any]) -> Dict[str, Any]:
  app = get_multiagent_graph()
  state = app.invoke({"params": params})
  use_case = str(state.get("use_case", params.get("use_case", "search")) or "search").strip().lower()
  return {
    "use_case": use_case,
    "error": state.get("error"),
    "result": state.get("result", {}),
  }
