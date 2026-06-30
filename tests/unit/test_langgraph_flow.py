import unittest

from multiagent.langgraph_flow import _parse_top_n_param


class TestLanggraphFlow(unittest.TestCase):
  def test_parse_top_n_preserves_zero_as_unlimited(self):
    self.assertEqual(_parse_top_n_param({"top_n": 0}), 0)

  def test_parse_top_n_defaults_only_when_missing_or_empty(self):
    self.assertEqual(_parse_top_n_param({}), 10)
    self.assertEqual(_parse_top_n_param({"top_n": ""}), 10)


if __name__ == "__main__":
  unittest.main()
