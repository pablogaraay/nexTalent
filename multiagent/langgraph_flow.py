from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

try:
  from config import Config
except ModuleNotFoundError:
  import sys
  from pathlib import Path
  BASE_DIR = Path(__file__).resolve().parent.parent
  if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
  from config import Config
from .services import UseCaseService


class GraphState(TypedDict, total=False):
  params: Dict[str, Any]
  offers: List[Dict[str, Any]]
  profile: Dict[str, Any]
  result: Dict[str, Any]
  error: str
  use_case: str


def build_multiagent_graph():
  service = UseCaseService()
  graph = StateGraph(GraphState)

  def load_data_node(state: GraphState) -> GraphState:
    try:
      offers = service.load_offers_for_analysis()
      params = state.get("params", {}) or {}
      use_case = str(params.get("use_case", "search") or "search").strip().lower()
      if use_case == "insights":
        use_case = "market_insights"
      if not offers:
        return {
          **state,
          "offers": [],
          "use_case": use_case,
          "error": f"No hay ofertas disponibles en la coleccion '{Config.MAPPED_COLL}'."
        }
      return {**state, "offers": offers, "use_case": use_case}
    except Exception as exc:
      return {**state, "offers": [], "error": f"Error cargando datos desde Mongo: {exc}"}

  def route_after_load(state: GraphState) -> str:
    if state.get("error"):
      return "end"
    use_case = str(state.get("use_case", "search") or "search").strip().lower()
    if use_case == "market_insights":
      return "market_insights"
    return "search"

  def parse_profile_node(state: GraphState) -> GraphState:
    if state.get("error"):
      return state
    params = state.get("params", {}) or {}
    try:
      profile = service.parse_profile(
        profile_text=params.get("profile_text", "") or "",
        cv_file=params.get("cv_file", "") or ""
      )
      return {**state, "profile": profile}
    except Exception as exc:
      return {
        **state,
        "error": f"Error parseando perfil con LLM: {exc}"
      }

  def search_node(state: GraphState) -> GraphState:
    if state.get("error"):
      return state
    try:
      params = state.get("params", {}) or {}
      top_n = int(params.get("top_n", 10) or 10)
      result = service.use_case_search(state.get("offers", []), state.get("profile", {}), top_n=top_n)
      return {**state, "result": result}
    except Exception as exc:
      return {
        **state,
        "error": f"Error en ranking LLM: {exc}"
      }

  def market_insights_node(state: GraphState) -> GraphState:
    if state.get("error"):
      return state
    try:
      params = state.get("params", {}) or {}
      top_n = int(params.get("top_n", 10) or 10)
      result = service.use_case_market_insights(state.get("offers", []), top_n=top_n)
      return {**state, "result": result}
    except Exception as exc:
      return {
        **state,
        "error": f"Error generando insights de mercado: {exc}"
      }

  graph.add_node("load_data", load_data_node)
  graph.add_node("parse_profile", parse_profile_node)
  graph.add_node("search", search_node)
  graph.add_node("market_insights", market_insights_node)

  graph.set_entry_point("load_data")
  graph.add_conditional_edges(
    "load_data",
    route_after_load,
    {
      "search": "parse_profile",
      "market_insights": "market_insights",
      "end": END
    }
  )
  graph.add_edge("parse_profile", "search")
  graph.add_edge("search", END)
  graph.add_edge("market_insights", END)

  return graph.compile()


def run_multiagent_flow(params: Dict[str, Any]) -> Dict[str, Any]:
  app = build_multiagent_graph()
  state = app.invoke({"params": params})
  use_case = str(state.get("use_case", params.get("use_case", "search")) or "search").strip().lower()
  return {
    "use_case": use_case,
    "error": state.get("error"),
    "result": state.get("result", {})
  }
