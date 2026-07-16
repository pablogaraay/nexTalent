import unittest
from unittest.mock import patch

from multiagent.langgraph_flow import _parse_top_n_param, build_multiagent_graph


class TestLanggraphFlow(unittest.TestCase):
  def test_parse_top_n_preserves_zero_as_unlimited(self):
    self.assertEqual(_parse_top_n_param({"top_n": 0}), 0)

  def test_parse_top_n_defaults_only_when_missing_or_empty(self):
    self.assertEqual(_parse_top_n_param({}), 10)
    self.assertEqual(_parse_top_n_param({"top_n": ""}), 10)

  def test_profile_parse_error_terminates_without_recursion(self):
    with patch("multiagent.langgraph_flow.ProfileService") as profile_service_cls, \
      patch("multiagent.langgraph_flow.SearchService"), \
      patch("multiagent.langgraph_flow.InsightsService"), \
      patch("multiagent.langgraph_flow.CareerService"), \
      patch("multiagent.langgraph_flow.OfferRepository") as offer_repository_cls:
      offer_repository_cls.return_value.count_mapped_offers.return_value = 1
      profile_service_cls.return_value.parse_profile.side_effect = RuntimeError("schema rejected")

      graph = build_multiagent_graph()
      state = graph.invoke({"params": {"use_case": "search", "profile_text": "Data analyst"}})

    self.assertIn("schema rejected", state["error"])
    self.assertNotIn("result", state)

  def test_career_flow_routes_to_skill_gap_and_plan(self):
    with patch("multiagent.langgraph_flow.ProfileService") as profile_service_cls, \
      patch("multiagent.langgraph_flow.SearchService"), \
      patch("multiagent.langgraph_flow.InsightsService"), \
      patch("multiagent.langgraph_flow.CareerService") as career_service_cls, \
      patch("multiagent.langgraph_flow.OfferRepository") as offer_repository_cls:
      offer_repository_cls.return_value.count_mapped_offers.return_value = 5
      profile_service_cls.return_value.parse_profile.return_value = {
        "role": "Data Analyst",
        "skills": ["Python", "SQL", "Power BI"],
      }
      profile_service_cls.return_value.assess_profile_signal.return_value = {
        "level": "strong",
        "score": 0.8,
        "reasons": [],
      }
      career_service_cls.return_value.use_case_career.return_value = {
        "target_role": "Data Engineer",
        "gaps": [{"skill_name": "AWS"}],
        "plan": {"phases": []},
      }

      graph = build_multiagent_graph()
      state = graph.invoke({
        "params": {
          "use_case": "career",
          "profile_text": "Analista con Python, SQL y Power BI",
          "target_role": "Data Engineer",
        }
      })

    self.assertEqual(state["result"]["target_role"], "Data Engineer")
    career_service_cls.return_value.use_case_career.assert_called_once()


if __name__ == "__main__":
  unittest.main()
