import unittest
import json
from pathlib import Path
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
    self.assertEqual(response.json()["error"], "Solo se aceptan archivos con extensión .pdf o .docx.")

  def test_search_rejects_oversized_cv(self):
    response = self.client.post(
      "/api/search",
      files={"cv": ("cv.pdf", b"x" * (api.MAX_CV_BYTES + 1), "application/pdf")},
    )

    self.assertEqual(response.status_code, 400)
    self.assertIn("10 MB", response.json()["error"])

  @patch("api.run_multiagent_flow")
  def test_search_accepts_docx_cv(self, multiagent_flow):
    multiagent_flow.return_value = {
      "use_case": "search",
      "error": None,
      "result": {"profile": {}, "total_candidates": 0, "results": []},
    }

    response = self.client.post(
      "/api/search",
      files={"cv": ("cv.docx", b"fake docx bytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    self.assertEqual(response.status_code, 200)
    params = multiagent_flow.call_args.kwargs["params"]
    self.assertEqual(Path(params["cv_file"]).suffix, ".docx")

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
  def test_search_returns_429_when_flow_reports_ai_rate_limit(self, multiagent_flow):
    multiagent_flow.return_value = {
      "use_case": "search",
      "error": "Error parseando perfil con LLM: Error code: 429 - rate_limit_exceeded on tokens per day",
      "result": {},
    }

    response = self.client.post("/api/search", data={"profileText": "Data engineer"})

    self.assertEqual(response.status_code, 429)
    self.assertEqual(response.json()["code"], "ai_rate_limit_exceeded")
    self.assertIn("límite diario", response.json()["error"])

  @patch("api.run_multiagent_flow")
  def test_search_returns_500_when_flow_reports_generic_error(self, multiagent_flow):
    multiagent_flow.return_value = {
      "use_case": "search",
      "error": "Error parseando perfil con LLM: schema rejected",
      "result": {},
    }

    response = self.client.post("/api/search", data={"profileText": "Data engineer"})

    self.assertEqual(response.status_code, 500)
    self.assertIn("schema rejected", response.json()["error"])

  def test_career_plan_requires_target_role(self):
    response = self.client.post("/api/career-plan", data={"profileText": "Python y SQL"})

    self.assertEqual(response.status_code, 400)
    self.assertIn("rol objetivo", response.json()["error"])

  @patch("api.run_multiagent_flow")
  def test_career_plan(self, multiagent_flow):
    multiagent_flow.return_value = {
      "use_case": "career",
      "error": None,
      "result": {
        "target_role": "Data Engineer",
        "readiness": {"score": 60},
        "gaps": [],
        "plan": {"phases": []},
      },
    }

    response = self.client.post(
      "/api/career-plan",
      data={"targetRole": "Data Engineer", "profileText": "Analista con Python y SQL"},
    )

    self.assertEqual(response.status_code, 200)
    params = multiagent_flow.call_args.kwargs["params"]
    self.assertEqual(params["use_case"], "career")
    self.assertEqual(params["target_role"], "Data Engineer")
    self.assertEqual(params["top_k"], 30)

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

  @patch("api.ExternalInsightsService")
  def test_insights_upload_raw_json(self, service_class):
    service = service_class.return_value
    service.use_case_insights_from_raw_json.return_value = {
      "source": "uploaded_raw_json",
      "summary": {"filtered_offers": 1},
      "top_jobs": [],
      "top_skills": [],
      "available_filters": {},
      "required_fields": ["url", "title"],
      "warnings": [],
    }
    raw_offers = [
      {
        "url": "external-1",
        "title": "Data Engineer",
        "company": "External",
        "city": "Madrid",
        "region": "Comunidad de Madrid",
        "country": "Spain",
        "role_raw": "Data Engineer",
        "hard_skills_raw": ["SQL"],
        "soft_skills_raw": [],
        "tools_raw": ["Python"],
        "seniority_raw": "junior",
      }
    ]

    response = self.client.post(
      "/api/insights/upload-raw",
      data={"topN": "7", "city": "Madrid", "jobFamily": "Data and AI"},
      files={"file": ("external.json", json.dumps(raw_offers).encode("utf-8"), "application/json")},
    )

    self.assertEqual(response.status_code, 200)
    payload = response.json()
    self.assertEqual(payload["source"], "uploaded_raw_json")
    self.assertEqual(payload["result"]["summary"]["filtered_offers"], 1)
    args, kwargs = service.use_case_insights_from_raw_json.call_args
    self.assertEqual(args[0][0]["url"], "external-1")
    self.assertEqual(kwargs["top_n"], 7)
    self.assertEqual(kwargs["filters"]["city"], "Madrid")
    self.assertEqual(kwargs["filters"]["job_family"], "Data and AI")

  def test_insights_upload_raw_json_rejects_non_json_file(self):
    response = self.client.post(
      "/api/insights/upload-raw",
      files={"file": ("external.txt", b"[]", "text/plain")},
    )

    self.assertEqual(response.status_code, 400)
    self.assertIn("Solo se aceptan", response.json()["error"])
    self.assertIn("role_raw", response.json()["required_fields"])
