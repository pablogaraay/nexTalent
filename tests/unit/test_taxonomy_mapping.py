import unittest
from unittest.mock import patch

from rag.index_taxonomy import MIN_SFIA_TAXONOMY_ROWS, validate_skill_taxonomy
from rag.map_offers import HARD_SKILL_LIMIT, SOFT_SKILL_LIMIT, best_match, build_exact_skill_index


class FakeCollection:
  def __init__(self, metadatas=None, distances=None):
    self.metadatas = metadatas or []
    self.distances = distances or []

  def get(self, include=None):
    return {"metadatas": self.metadatas}

  def query(self, query_embeddings, n_results, include=None):
    return {
      "metadatas": [self.metadatas[:n_results]],
      "distances": [self.distances[:n_results]],
    }


class TestTaxonomyValidation(unittest.TestCase):
  def valid_rows(self):
    rows = [
      {
        "skill_id": f"SFIA_SKILL_{index}",
        "skill_name": f"Skill {index}",
        "item_type": "skill",
      }
      for index in range(MIN_SFIA_TAXONOMY_ROWS - 1)
    ]
    rows.append({
      "skill_id": "SFIA_ATTR_COLLABORATION",
      "skill_name": "Colaboracion",
      "item_type": "attribute",
    })
    return rows

  def test_accepts_complete_taxonomy_with_skills_and_attributes(self):
    rows = self.valid_rows()
    self.assertEqual(validate_skill_taxonomy(rows), rows)

  def test_rejects_incomplete_taxonomy(self):
    with self.assertRaisesRegex(ValueError, "incompleta"):
      validate_skill_taxonomy(self.valid_rows()[:-1])

  def test_rejects_missing_item_type(self):
    rows = self.valid_rows()
    rows[0]["item_type"] = ""
    with self.assertRaisesRegex(ValueError, "item_type"):
      validate_skill_taxonomy(rows)


class TestSkillMapping(unittest.TestCase):
  def setUp(self):
    self.metadatas = [
      {"skill_id": "ATTR_COLL", "skill_name": "Colaboracion", "item_type": "attribute"},
      {"skill_id": "SKILL_ORGF", "skill_name": "Facilitacion organizativa", "item_type": "skill"},
      {"skill_id": "ATTR_COMM", "skill_name": "Comunicacion", "item_type": "attribute"},
    ]

  def test_exact_match_respects_item_type(self):
    collection = FakeCollection(self.metadatas, [0.1, 0.11, 0.2])
    exact_index = build_exact_skill_index(collection)
    result = best_match(
      collection,
      "colaboracion",
      0.72,
      expected_item_type="attribute",
      exact_index=exact_index,
    )
    self.assertEqual(result["status"], "mapped")
    self.assertEqual(result["method"], "exact_name")
    self.assertEqual(result["top1"]["metadata"]["skill_id"], "ATTR_COLL")

  def test_hard_mapping_is_more_conservative_than_soft_mapping(self):
    self.assertGreater(HARD_SKILL_LIMIT, SOFT_SKILL_LIMIT)

  @patch("rag.map_offers.embed_text", return_value=[0.1, 0.2])
  def test_semantic_match_filters_wrong_item_type(self, _embed):
    collection = FakeCollection(self.metadatas, [0.05, 0.06, 0.20])
    result = best_match(
      collection,
      "trabajo en equipo",
      0.72,
      expected_item_type="attribute",
      min_margin=0.03,
      strong_score=0.82,
    )
    self.assertEqual(result["top1"]["metadata"]["skill_id"], "ATTR_COLL")
    self.assertNotEqual(result["top1"]["metadata"]["skill_id"], "SKILL_ORGF")

  @patch("rag.map_offers.embed_text", return_value=[0.1, 0.2])
  def test_marks_close_candidates_as_ambiguous(self, _embed):
    collection = FakeCollection(
      [self.metadatas[0], self.metadatas[2]],
      [0.25, 0.26],
    )
    result = best_match(
      collection,
      "habilidad generica",
      0.72,
      expected_item_type="attribute",
      min_margin=0.03,
      strong_score=0.82,
    )
    self.assertEqual(result["status"], "ambiguous")


if __name__ == "__main__":
  unittest.main()
