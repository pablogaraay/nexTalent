import unittest

from rag.index_technology_taxonomy import (
  MIN_TECHNOLOGY_TAXONOMY_ROWS,
  build_embedding_document,
  validate_technology_taxonomy,
)


class TestTechnologyTaxonomyIndex(unittest.TestCase):
  def valid_rows(self):
    return [
      {
        "technology_id": f"TECH_{index}",
        "preferred_label": f"Technology {index}",
        "aliases": [],
        "category_id": "programming",
      }
      for index in range(MIN_TECHNOLOGY_TAXONOMY_ROWS)
    ]

  def test_accepts_complete_taxonomy(self):
    rows = self.valid_rows()
    self.assertEqual(validate_technology_taxonomy(rows), rows)

  def test_rejects_duplicate_id(self):
    rows = self.valid_rows()
    rows[1]["technology_id"] = rows[0]["technology_id"]
    with self.assertRaisesRegex(ValueError, "duplicado"):
      validate_technology_taxonomy(rows)

  def test_embedding_includes_label_aliases_and_category(self):
    document = build_embedding_document({
      "preferred_label": "Amazon Web Services (AWS)",
      "aliases": ["AWS", "Amazon Web Services"],
      "category_id": "cloud",
    })
    self.assertIn("AWS", document)
    self.assertIn("Amazon Web Services", document)
    self.assertIn("cloud", document)


if __name__ == "__main__":
  unittest.main()
