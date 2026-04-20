from __future__ import annotations

from typing import Any, Dict, List

from repositories.offer_repository import OfferRepository

from .llm_client import LLMClientService
from .services.insights_service import InsightsService
from .services.planner_service import PlannerService
from .services.profile_service import ProfileService
from .services.search_service import SearchService


class UseCaseService:
  def __init__(self):
    self.llm_client_service = LLMClientService()
    self.offer_repository = OfferRepository()

    self.profile_service = ProfileService(self.llm_client_service)
    self.planner_service = PlannerService(self.llm_client_service)
    self.search_service = SearchService(self.llm_client_service)
    self.insights_service = InsightsService()

  def load_offers_for_analysis(self) -> List[Dict[str, Any]]:
    return self.offer_repository.load_mapped_offers() or []

  def parse_profile(self, profile_text: str = "", cv_file: str = "") -> Dict[str, Any]:
    return self.profile_service.parse_profile(profile_text=profile_text, cv_file=cv_file)

  def assess_profile_signal(self, profile: Dict[str, Any]) -> Dict[str, Any]:
    return self.profile_service.assess_profile_signal(profile)

  def enrich_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
    return self.profile_service.enrich_profile(profile)

  def decide_search_plan(self, profile: Dict[str, Any]) -> Dict[str, Any]:
    return self.planner_service.decide_search_plan(profile)

  def use_case_search(
    self,
    offers: List[Dict[str, Any]],
    profile: Dict[str, Any],
    top_n: int = 10,
    plan: Dict[str, Any] | None = None,
  ) -> Dict[str, Any]:
    return self.search_service.use_case_search(
      offers=offers,
      profile=profile,
      top_n=top_n,
      plan=plan,
      default_plan=self.planner_service.default_search_plan(),
      coerce_plan=self.planner_service.coerce_search_plan,
    )

  def use_case_insights(self, offers: List[Dict[str, Any]], top_n: int = 10) -> Dict[str, Any]:
    return self.insights_service.use_case_insights(offers=offers, top_n=top_n)
