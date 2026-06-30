import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import api


class TestApi(unittest.TestCase):
  def setUp(self):
    self.client = TestClient(api.app)

  def test_health(self):
    response = self.client.get("/api/health")

    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.json()["ok"])
    self.assertIn("timestamp", response.json())

  def test_search_without_input(self):
    response = self.client.post("/api/search", data={})

    self.assertEqual(response.status_code, 400)
    self.assertIn("Debes enviar", response.json()["error"])

  def test_search_with_invalid_file(self):
    response = self.client.post(
      "/api/search",
      files={"cv": ("cv.txt", b"plain text cv", "text/plain")},
    )

    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.json()["error"], "Solo se aceptan archivos con extensión .pdf.")

  @patch("api.run_multiagent_flow")
  def test_search(self, multiagent_flow):
    multiagent_flow.return_value = {
      "use_case": "search",
      "error": None,
      "result": {
        "profile": {"role": "data engineer"},
        "total_candidates": 1,
        "results": [
          {
            "url": "https://example.com/job/1",
            "title": "Data Engineer",
            "company": "Deloitte",
            "matched_skills": ["Python"],
          }
        ],
      },
    }

    response = self.client.post("/api/search", data={"profileText": "Data engineer with Python"})

    self.assertEqual(response.status_code, 200)
    payload = response.json()
    self.assertEqual(payload["use_case"], "search")
    self.assertEqual(payload["result"]["profile"]["role"], "data engineer")
    multiagent_flow.assert_called_once()
    params = multiagent_flow.call_args.kwargs["params"]
    self.assertEqual(params["use_case"], "search")
    self.assertEqual(params["profile_text"], "Data engineer with Python")
    self.assertEqual(params["top_n"], 0)

  @patch("api.run_multiagent_flow")
  def test_insights(self, multiagent_flow):
    multiagent_flow.return_value = {
      "use_case": "insights",
      "error": None,
      "result": {
        "summary": {"filtered_offers": 1},
        "top_jobs": [],
        "top_skills": [],
        "available_filters": {},
      },
    }

    response = self.client.get(
      "/api/insights",
      params={
        "topN": "3",
        "company": "Deloitte",
        "city": "Madrid",
        "region": "Comunidad de Madrid",
        "seniority": "senior",
        "jobFamily": "Data and AI",
      },
    )

    self.assertEqual(response.status_code, 200)
    params = multiagent_flow.call_args.kwargs["params"]
    self.assertEqual(params["use_case"], "insights")
    self.assertEqual(params["top_n"], 3)
    self.assertEqual(params["company"], "Deloitte")
    self.assertEqual(params["city"], "Madrid")
    self.assertEqual(params["region"], "Comunidad de Madrid")
    self.assertEqual(params["seniority"], "senior")
    self.assertEqual(params["job_family"], "Data and AI")
