import unittest

from helpers import load_mock_data
from multiagent.services.insights_service import InsightsService


class FakeTaxonomyRepository:
  def load_offers(self, collection, active_only=False, projection=None):
    return [
      {
        "job_id": "JOB_DATA_ENGINEER",
        "occupation": "Data Engineer",
        "active": True,
      },
      {
        "job_id": "JOB_ANALYTICS_ENGINEER",
        "occupation": "Analytics Engineer",
        "active": True,
      },
      {
        "job_id": "JOB_CLOUD_CONSULTANT",
        "occupation": "Cloud Consultant",
        "active": True,
      },
      {
        "job_id": "JOB_INACTIVE",
        "occupation": "Inactive Role",
        "active": False,
      },
    ]


class TestInsightsService(unittest.TestCase):
  def setUp(self):
    self.offers = load_mock_data("offers_mapped_sample.json")
    self.service = InsightsService(taxonomy_repository=FakeTaxonomyRepository())

  def test_summary_and_rankings(self):
    result = self.service.use_case_insights(self.offers, top_n=5)

    self.assertEqual(result["summary"]["total_offers"], 3)
    self.assertEqual(result["summary"]["filtered_offers"], 3)
    self.assertEqual(result["summary"]["offers_with_job_mapping"], 3)
    self.assertEqual(result["summary"]["offers_with_skills_sfia"], 3)
    self.assertEqual(result["summary"]["offers_with_technologies_onet"], 3)
    self.assertEqual(result["top_jobs"][0]["job_title"], "Data Engineer")
    self.assertEqual(result["top_skills"][0]["skill_name"], "SQL")
    self.assertEqual(result["top_skills"][0]["demand"], 2)
    self.assertEqual(result["top_technologies"][0]["preferred_label"], "Python")
    self.assertEqual(result["top_technologies"][0]["demand"], 2)
    self.assertIn(
      {"value": "Deloitte", "count": 2},
      result["available_filters"]["companies"],
    )

  def test_company_location_and_seniority_filters(self):
    filters = {
      "company": "Deloitte",
      "city": "Madrid",
      "region": "Comunidad de Madrid",
      "seniority": "senior",
    }

    result = self.service.use_case_insights(self.offers, top_n=5, filters=filters)

    self.assertEqual(result["summary"]["filtered_offers"], 1)
    self.assertEqual(result["applied_filters"]["company"], "Deloitte")
    self.assertEqual(result["top_jobs"][0]["job_id"], "JOB_DATA_ENGINEER")
    self.assertEqual(result["top_skills"][0]["skill_name"], "SQL")

  def test_job_family_filter(self):
    filters = {"job_family": "Cloud"}

    result = self.service.use_case_insights(self.offers, top_n=5, filters=filters)

    self.assertEqual(result["summary"]["filtered_offers"], 1)
    self.assertEqual(result["top_jobs"][0]["job_family"], "Cloud")
    self.assertEqual(result["top_skills"][0]["skill_name"], "Cloud computing")
