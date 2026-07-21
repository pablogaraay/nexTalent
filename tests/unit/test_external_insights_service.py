import unittest

from multiagent.services.external_insights_service import ExternalInsightsService
from multiagent.services.insights_service import InsightsService


class FakeLLMClientService:
  def embed_text(self, text):
    return text


class FakeCollection:
  def __init__(self, kind):
    self.kind = kind

  def query(self, query_embeddings, n_results=3, include=None):
    query = str(query_embeddings[0]).lower()
    if self.kind == "jobs" and "data engineer" in query:
      return {
        "metadatas": [[{"job_id": "JOB_DATA_ENGINEER", "job_family": "Data and AI"}]],
        "distances": [[0.08]],
      }
    if self.kind == "skills" and "python" in query:
      return {
        "metadatas": [[{"skill_id": "SKILL_PY", "skill_name": "Python"}]],
        "distances": [[0.06]],
      }
    if self.kind == "skills" and "sql" in query:
      return {
        "metadatas": [[{"skill_id": "SKILL_SQL", "skill_name": "SQL"}]],
        "distances": [[0.09]],
      }
    if self.kind == "technologies" and "python" in query:
      return {
        "metadatas": [[{
          "technology_id": "TECH_PYTHON",
          "preferred_label": "Python",
          "aliases": "",
          "category_id": "programming",
        }]],
        "distances": [[0.04]],
      }
    return {"metadatas": [[]], "distances": [[]]}

  def get(self, include=None):
    if self.kind == "technologies":
      return {"metadatas": [{
        "technology_id": "TECH_PYTHON",
        "preferred_label": "Python",
        "aliases": "",
        "category_id": "programming",
      }]}
    return {"metadatas": []}


class FakeVectorStore:
  def get_collection(self, name):
    if "technolog" in name:
      return FakeCollection("technologies")
    if "skill" in name:
      return FakeCollection("skills")
    return FakeCollection("jobs")


class FakeTaxonomyRepository:
  def load_offers(self, collection, active_only=False, projection=None):
    return [
      {
        "job_id": "JOB_DATA_ENGINEER",
        "occupation": "Data Engineer",
        "active": True,
      }
    ]


class TestExternalInsightsService(unittest.TestCase):
  def setUp(self):
    self.service = ExternalInsightsService(
      llm_client_service=FakeLLMClientService(),
      vector_store=FakeVectorStore(),
      insights_service=InsightsService(taxonomy_repository=FakeTaxonomyRepository()),
    )

  def test_maps_raw_json_and_calculates_insights(self):
    raw_offers = [
      {
        "url": "external-1",
        "title": "Data Engineer",
        "company": "External",
        "city": "Madrid",
        "region": "Comunidad de Madrid",
        "country": "Spain",
        "role_raw": "Data Engineer",
        "hard_skills_raw": ["SQL"],
        "soft_skills_raw": [],
        "tools_raw": ["Python"],
        "seniority_raw": "junior",
      }
    ]

    result = self.service.use_case_insights_from_raw_json(raw_offers, top_n=5)

    self.assertEqual(result["source"], "uploaded_raw_json")
    self.assertEqual(result["summary"]["total_offers"], 1)
    self.assertEqual(result["top_jobs"][0]["job_title"], "Data Engineer")
    self.assertEqual(
      {item["skill_name"] for item in result["top_skills"]},
      {"SQL"},
    )
    self.assertTrue(all(item["demand"] == 1 for item in result["top_skills"]))
    self.assertEqual(result["top_technologies"][0]["preferred_label"], "Python")
    self.assertEqual(result["summary"]["technologies_onet_coverage_pct"], 100.0)

  def test_rejects_non_array_json(self):
    with self.assertRaises(ValueError):
      self.service.use_case_insights_from_raw_json({"url": "external-1"})


if __name__ == "__main__":
  unittest.main()
