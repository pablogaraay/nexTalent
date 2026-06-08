import unittest

from utils.text import is_unknown_value, normalize_text, offer_location_string, unique_keep_order


class TestTextUtils(unittest.TestCase):
  def test_normalize_text(self):
    self.assertEqual(normalize_text("  Data Engineer  "), "data engineer")

  def test_unknown_values(self):
    values = ["", "unknown", "N/A", "desconocido", " null "]

    for value in values:
      self.assertTrue(is_unknown_value(value))

  def test_unique_values(self):
    skills = ["Python", " SQL ", "python", "", "SQL", "AWS"]

    self.assertEqual(unique_keep_order(skills), ["Python", "SQL", "AWS"])

  def test_offer_location(self):
    offer = {
      "city": "Madrid",
      "region": "Comunidad de Madrid",
      "country": "Spain",
      "location_raw": "Madrid, Comunidad de Madrid, Spain",
    }
    expected = "Madrid | Comunidad de Madrid | Spain | Madrid, Comunidad de Madrid, Spain"

    self.assertEqual(offer_location_string(offer), expected)
