import unittest

from rag.technology_mapping import (
  build_exact_technology_index,
  match_technology,
  normalize_technology_term,
)


class FakeCollection:
  def __init__(self, metadatas, distances=None):
    self.metadatas = metadatas
    self.distances = distances or [0.05] * len(metadatas)

  def get(self, include=None):
    return {"metadatas": self.metadatas}

  def query(self, query_embeddings, n_results, include=None):
    return {
      "metadatas": [self.metadatas[:n_results]],
      "distances": [self.distances[:n_results]],
    }


class TestTechnologyMapping(unittest.TestCase):
  def test_exact_alias_mapping(self):
    collection = FakeCollection([{
      "technology_id": "TECH_AWS",
      "preferred_label": "Amazon Web Services (AWS)",
      "aliases": "AWS | Amazon Web Services",
      "category_id": "cloud",
    }])
    exact_index = build_exact_technology_index(collection)
    result = match_technology(collection, "aws", lambda _: [0.1], exact_index=exact_index)
    self.assertEqual(result["status"], "mapped")
    self.assertEqual(result["method"], "exact_label_or_alias")
    self.assertEqual(result["top1"]["metadata"]["technology_id"], "TECH_AWS")

  def test_normalization_preserves_programming_language_symbols(self):
    self.assertNotEqual(normalize_technology_term("C"), normalize_technology_term("C++"))
    self.assertNotEqual(normalize_technology_term("C"), normalize_technology_term("C#"))

  def test_ambiguous_semantic_match_abstains(self):
    collection = FakeCollection(
      [
        {"technology_id": "TECH_ONE", "preferred_label": "One"},
        {"technology_id": "TECH_TWO", "preferred_label": "Two"},
      ],
      [0.12, 0.13],
    )
    result = match_technology(collection, "ambiguous", lambda _: [0.1], limit=0.85)
    self.assertEqual(result["status"], "ambiguous")

  def test_can_disable_semantic_mapping_for_hard_skill_fallback(self):
    collection = FakeCollection([
      {"technology_id": "TECH_SQL", "preferred_label": "SQL", "aliases": ""},
    ])
    result = match_technology(
      collection,
      "database querying",
      lambda _: [0.1],
      exact_index=build_exact_technology_index(collection),
      allow_semantic=False,
    )
    self.assertEqual(result["status"], "unmapped")


if __name__ == "__main__":
  unittest.main()
