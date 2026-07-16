import unittest

from multiagent.services.career_service import CareerService


class NoopLLMClient:
  def embed_text(self, text):
    return [0.1, 0.2]


class NoopVectorStore:
  def get_collection(self, name):
    raise RuntimeError("taxonomy unavailable in deterministic test")


class NoopRepository:
  pass


class TaxonomyRepository:
  def load_offers(self, collection, active_only=False, projection=None):
    return [
      {"skill_id": "SFIA_SKILL_DATA", "item_type": "skill"},
      {"skill_id": "SFIA_ATTR_COMM", "item_type": "attribute"},
    ]


class TestCareerService(unittest.TestCase):
  def setUp(self):
    self.service = CareerService(
      llm_client_service=NoopLLMClient(),
      vector_store=NoopVectorStore(),
      offer_repository=NoopRepository(),
    )
    self.offers = [
      {
        "title": "Data Engineer",
        "company": "A",
        "url": "url-a",
        "skills_sfia": [
          {"skill_id": "PY", "skill_name": "Python", "raw": "Python", "item_type": "skill"},
          {"skill_id": "SQL", "skill_name": "SQL", "raw": "SQL", "item_type": "skill"},
          {"skill_id": "AWS", "skill_name": "AWS", "raw": "Amazon Web Services", "item_type": "skill"},
          {"skill_id": "COMM", "skill_name": "Communication", "raw": "Communication", "item_type": "attribute"},
          {"skill_id": "COLL", "skill_name": "Collaboration", "raw": "Teamwork", "item_type": "attribute"},
        ],
      },
      {
        "title": "Data Engineer",
        "company": "B",
        "url": "url-b",
        "skills_sfia": [
          {"skill_id": "PY", "skill_name": "Python", "raw": "Python", "item_type": "skill"},
          {"skill_id": "SQL", "skill_name": "SQL", "raw": "SQL", "item_type": "skill"},
          {"skill_id": "COMM", "skill_name": "Communication", "raw": "Communication", "item_type": "attribute"},
        ],
      },
      {
        "title": "Data Engineer",
        "company": "C",
        "url": "url-c",
        "skills_sfia": [
          {"skill_id": "PY", "skill_name": "Python", "raw": "Python", "item_type": "skill"},
          {"skill_id": "DB", "skill_name": "Database design", "raw": "Data modelling", "item_type": "skill"},
        ],
      },
    ]

  def test_builds_weighted_gap_and_personalized_plan(self):
    result = self.service.use_case_career(
      profile={"role": "Data Analyst", "skills": ["Python", "Communication"]},
      target_role="Data Engineer",
      offers=self.offers,
    )

    self.assertEqual(result["target_role"], "Data Engineer")
    self.assertEqual(result["market"]["offers_analyzed"], 3)
    self.assertEqual(result["strengths"][0]["skill_name"], "Python")
    self.assertEqual(result["readiness"]["score"], 50)
    self.assertEqual(result["readiness"]["by_type"]["hard"]["score"], 43)
    self.assertEqual(result["readiness"]["by_type"]["soft"]["score"], 67)
    self.assertEqual(
      [skill["skill_name"] for skill in result["strengths_by_type"]["soft"]],
      ["Communication"],
    )

    gaps = {gap["skill_name"]: gap for gap in result["gaps"]}
    self.assertEqual(gaps["SQL"]["priority"], "critical")
    self.assertEqual(gaps["AWS"]["priority"], "recommended")
    self.assertEqual(gaps["Database design"]["priority"], "recommended")
    self.assertEqual(gaps["Collaboration"]["skill_type"], "soft")
    hard_track = next(track for track in result["plan"]["tracks"] if track["skill_type"] == "hard")
    soft_track = next(track for track in result["plan"]["tracks"] if track["skill_type"] == "soft")
    self.assertEqual(hard_track["phases"][0]["weeks"], "Semanas 1-4")
    self.assertIn("SQL", hard_track["phases"][0]["skills"])
    self.assertIn("feedback", " ".join(soft_track["phases"][0]["actions"]).lower())

  def test_rejects_analysis_without_target_offers(self):
    with self.assertRaisesRegex(ValueError, "No hay ofertas suficientes"):
      self.service.use_case_career(
        profile={"skills": ["Python"]},
        target_role="Quantum Architect",
        offers=[],
      )

  def test_classifies_existing_mapped_skills_from_sfia_taxonomy(self):
    service = CareerService(
      llm_client_service=NoopLLMClient(),
      vector_store=NoopVectorStore(),
      offer_repository=TaxonomyRepository(),
    )
    result = service.use_case_career(
      profile={"skills": ["Communication"]},
      target_role="Data Analyst",
      offers=[{
        "skills_sfia": [
          {"skill_id": "SFIA_SKILL_DATA", "skill_name": "Data analysis", "raw": "Data analysis"},
          {"skill_id": "SFIA_ATTR_COMM", "skill_name": "Communication", "raw": "Communication"},
        ],
      }],
    )

    self.assertEqual(result["strengths_by_type"]["soft"][0]["skill_name"], "Communication")
    self.assertEqual(result["gaps_by_type"]["hard"][0]["skill_name"], "Data analysis")
    self.assertEqual(result["readiness"]["by_type"]["soft"]["score"], 100)
    self.assertEqual(result["readiness"]["by_type"]["hard"]["score"], 0)


if __name__ == "__main__":
  unittest.main()
