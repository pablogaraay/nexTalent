import unittest

from scripts.build_technology_taxonomy import (
  build_taxonomy,
  build_taxonomy_evidence,
  canonical_label,
  infer_category,
  technology_id,
  validate_taxonomy,
)


class TestTechnologyTaxonomyBuilder(unittest.TestCase):
  def test_normalizes_common_onet_labels(self):
    self.assertEqual(canonical_label("Structured query language SQL"), "SQL")
    self.assertEqual(canonical_label("Amazon Web Services AWS software"), "Amazon Web Services (AWS)")
    self.assertEqual(canonical_label("Microsoft Power BI"), "Power BI")
    self.assertEqual(canonical_label("Microsoft Excel"), "Excel")

  def test_builds_stable_ids_for_punctuation_heavy_labels(self):
    self.assertEqual(technology_id("C++"), "TECH_C_PLUS_PLUS")
    self.assertEqual(technology_id("C#"), "TECH_C_SHARP")
    self.assertEqual(technology_id(".NET Framework"), "TECH_DOTNET_FRAMEWORK")

  def test_overrides_incorrect_onet_category_for_pytorch(self):
    self.assertEqual(
      infer_category("PyTorch", {"Data base user interface and query software"}),
      "ai_ml",
    )

  def test_aggregates_occupation_evidence(self):
    payload = {
      "data_dictionary": "https://example.test/dictionary/30.4/json/software_skills.html",
      "row": [
        {
          "onetsoc_code": "15-0001.00",
          "title": "Example occupation",
          "workplace_example": "Microsoft Power BI",
          "element_id": "2.E.1",
          "element_name": "Business intelligence and data analysis software",
          "hot_technology": "Y",
          "in_demand": "Y",
        },
        {
          "onetsoc_code": "15-0002.00",
          "title": "Second occupation",
          "workplace_example": "Microsoft Power BI",
          "element_id": "2.E.1",
          "element_name": "Business intelligence and data analysis software",
          "hot_technology": "Y",
          "in_demand": "N",
        },
      ],
    }
    documents = build_taxonomy_evidence(payload, limit=10)
    self.assertEqual(len(documents), 1)
    power_bi = documents[0]
    self.assertEqual(power_bi["technology_id"], "TECH_POWER_BI")
    self.assertEqual(power_bi["aliases"], ["Microsoft Power BI", "PowerBI"])
    self.assertEqual(power_bi["category_id"], "business_intelligence")
    self.assertEqual(power_bi["relevance"]["occupation_count"], 2)
    self.assertEqual(power_bi["relevance"]["in_demand_occupation_count"], 1)

    compact_documents = build_taxonomy(payload, limit=10)
    validate_taxonomy(compact_documents)
    self.assertEqual(set(compact_documents[0]), {
      "technology_id", "preferred_label", "aliases", "category_id",
    })


if __name__ == "__main__":
  unittest.main()
