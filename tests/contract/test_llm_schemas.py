import unittest

import schemas
from helpers import run_silently
from llm_processor import LLMProcessor


class FakeMongo:
  def __init__(self):
    self.saved_offers = []

  def upsert_bulk_offers(self, collection, offers, stage_prefix):
    self.saved_offers.extend(offers)


class TestLLMContract(unittest.TestCase):
  def test_extraction_schema(self):
    schema = schemas.build_extraction_schema()
    offer_schema = schema["properties"]["ofertas"]["items"]
    expected_fields = {
      "role_raw",
      "hard_skills_raw",
      "soft_skills_raw",
      "tools_raw",
      "seniority_raw",
      "work_modality_raw",
      "employment_type_raw",
    }

    self.assertEqual(schema["required"], ["ofertas"])
    self.assertFalse(schema["additionalProperties"])
    self.assertFalse(offer_schema["additionalProperties"])
    self.assertEqual(set(offer_schema["required"]), expected_fields)

  def test_profile_schema(self):
    schema = schemas.build_profile_parse_schema(["junior", "senior", "unknown"])
    expected_fields = {
      "role",
      "performed_roles",
      "role_experiences",
      "skills",
      "seniority_raw",
      "seniority_raw_targets",
      "location_query",
      "location_targets",
    }

    self.assertEqual(set(schema["required"]), expected_fields)
    self.assertFalse(schema["additionalProperties"])

  def test_merge_results(self):
    processor = object.__new__(LLMProcessor)
    offers = [{
      "title": "Data Engineer",
      "company": "Deloitte",
      "description_clean": "Python and SQL",
      "url": "https://example.com/1",
    }]
    llm_output = [{
      "role_raw": "data engineer",
      "hard_skills_raw": ["SQL"],
      "soft_skills_raw": [],
      "tools_raw": ["Python"],
      "seniority_raw": "",
      "work_modality_raw": "",
      "employment_type_raw": "",
    }]

    result = processor.merge_results(offers, llm_output)[0]

    self.assertEqual(result["title"], "Data Engineer")
    self.assertEqual(result["role_raw"], "data engineer")
    self.assertEqual(result["tools_raw"], ["Python"])

  def test_failed_llm_batch(self):
    processor = object.__new__(LLMProcessor)
    processor.db = FakeMongo()
    processor.call_model = lambda *args, **kwargs: []
    offers = [{
      "title": "Data Engineer",
      "company": "Deloitte",
      "description_clean": "Python and SQL",
      "url": "https://example.com/1",
    }]

    saved_count = run_silently(processor.process_batch, offers)
    saved_offer = processor.db.saved_offers[0]

    self.assertEqual(saved_count, 1)
    self.assertEqual(len(processor.db.saved_offers), 1)
    self.assertTrue(saved_offer["llm_error"])
    self.assertEqual(saved_offer["hard_skills_raw"], [])
    self.assertEqual(saved_offer["soft_skills_raw"], [])
    self.assertEqual(saved_offer["tools_raw"], [])
    self.assertEqual(saved_offer["role_raw"], "")
    self.assertEqual(saved_offer["seniority_raw"], "")
