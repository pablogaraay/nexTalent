import unittest

import pandas as pd

from helpers import create_data_wrangler, load_mock_data, run_silently
from rag.index_offers import build_offer_document, build_offer_metadata


class TestDataPipeline(unittest.TestCase):
  def setUp(self):
    self.wrangler = create_data_wrangler()

  def test_data_pipeline(self):
    raw_offers = pd.DataFrame(load_mock_data("offers_raw_sample.json"))

    structured = run_silently(self.wrangler.structure_data, raw_offers)
    valid, invalid = self.wrangler.filter_valid_offers(structured)
    target_companies = self.wrangler.filter_company_by_kw(valid)
    cleaned = self.wrangler.clean_description(target_companies)

    self.assertEqual(len(structured), 4)
    self.assertEqual(len(valid), 3)
    self.assertEqual(len(invalid), 1)
    self.assertEqual(set(cleaned["company"]), {"Deloitte", "Accenture"})
    self.assertTrue(cleaned["description_clean"].str.contains(" ").all())
    self.assertEqual(cleaned.loc[cleaned["company"] == "Deloitte", "city"].iloc[0], "Madrid")

  def test_chroma_document(self):
    offer = load_mock_data("offers_mapped_sample.json")[0]

    document = build_offer_document(offer)
    metadata = build_offer_metadata(offer)
    expected_text = [
      "role: data engineer",
      "company: Deloitte",
      "seniority: senior",
      "city: Madrid",
      "hard_skills: SQL",
      "tools: Python",
      "normalized_technologies: Python",
    ]

    for text in expected_text:
      self.assertIn(text, document)
    self.assertEqual(metadata["url"], "https://www.linkedin.com/jobs/view/1001")
    self.assertEqual(metadata["company"], "Deloitte")
