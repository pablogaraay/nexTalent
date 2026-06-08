import unittest

import pandas as pd

from helpers import create_data_wrangler, run_silently


class TestDataWrangler(unittest.TestCase):
  def setUp(self):
    self.wrangler = create_data_wrangler()

  def test_structure_location(self):
    offers = pd.DataFrame([{
      "_id": "1",
      "title": "Data Engineer",
      "company": "Deloitte",
      "location": "Madrid, Comunidad de Madrid, Spain",
      "url": "https://example.com/job/1",
      "description": "Job offer with Python",
    }])

    result = run_silently(self.wrangler.structure_data, offers)

    self.assertNotIn("_id", result.columns)
    self.assertEqual(result.loc[0, "location_raw"], "Madrid, Comunidad de Madrid, Spain")
    self.assertEqual(result.loc[0, "description_raw"], "Job offer with Python")
    self.assertTrue(result.loc[0, "location_structured"])
    self.assertEqual(result.loc[0, "city"], "Madrid")
    self.assertEqual(result.loc[0, "region"], "Comunidad de Madrid")
    self.assertEqual(result.loc[0, "country"], "Spain")

  def test_filter_invalid_offers(self):
    offers = pd.DataFrame([
      {"url": "u1", "title": "T1", "company": "Deloitte", "location_raw": "Madrid", "description_raw": "Text"},
      {"url": "u2", "title": "T2", "company": "Deloitte", "location_raw": "Madrid", "description_raw": ""},
      {"url": "", "title": "T3", "company": "Deloitte", "location_raw": "Madrid", "description_raw": "Text"},
    ])

    valid, invalid = self.wrangler.filter_valid_offers(offers)

    self.assertEqual(valid["url"].tolist(), ["u1"])
    self.assertEqual(len(invalid), 2)

  def test_filter_target_companies(self):
    offers = pd.DataFrame([
      {"company": "Deloitte Spain", "url": "u1"},
      {"company": "Accenture", "url": "u2"},
      {"company": "Other Company", "url": "u3"},
    ])

    result = self.wrangler.filter_company_by_kw(offers)

    self.assertEqual(result["url"].tolist(), ["u1", "u2"])

  def test_clean_description(self):
    offers = pd.DataFrame([{
      "description_raw": "Hello.World\twith   spaces\r\n\r\nNew line",
    }])

    result = self.wrangler.clean_description(offers)

    self.assertEqual(result.loc[0, "description_clean"], "Hello. World with spaces\nNew line")
