import unittest

from multiagent.services.search_service import SearchService


class FakeLLMClient:
  def embed_text(self, text):
    return [0.1, 0.2, 0.3]


class FakeVectorStore:
  def query(self, collection_name, query_embedding, n_results, include=None):
    return {
      "metadatas": [[{"url": "url-2"}, {"url": "url-1"}]],
      "distances": [[0.05, 0.10]],
    }


class FakeOfferRepository:
  def __init__(self):
    self.requested_urls = []
    self.requested_projection = None

  def load_mapped_offers_by_urls(self, urls, projection=None):
    self.requested_urls = list(urls)
    self.requested_projection = projection
    return [
      {
        "url": "url-1",
        "title": "Data Engineer",
        "company": "Deloitte",
        "city": "Madrid",
        "hard_skills_raw": ["Python"],
      },
      {
        "url": "url-2",
        "title": "Analytics Engineer",
        "company": "Accenture",
        "city": "Barcelona",
        "hard_skills_raw": ["SQL"],
      },
    ]


class TestSearchServiceQueries(unittest.TestCase):
  def test_hydrates_only_vector_candidate_urls_when_offers_are_not_preloaded(self):
    repo = FakeOfferRepository()
    service = SearchService(
      llm_client_service=FakeLLMClient(),
      vector_store=FakeVectorStore(),
      offer_repository=repo,
    )

    result = service.use_case_search(
      offers=[],
      profile={"role": "Data Engineer", "skills": ["Python"]},
      top_n=2,
      plan={"strategy": "vector_only", "top_k_hint": 2, "source": "test"},
      default_plan={"strategy": "vector_only", "top_k_hint": 2},
      coerce_plan=lambda plan: plan,
      total_candidates=100,
    )

    self.assertEqual(repo.requested_urls, ["url-2", "url-1"])
    self.assertIsNotNone(repo.requested_projection)
    self.assertEqual(result["total_candidates"], 100)
    self.assertEqual([offer["url"] for offer in result["results"]], ["url-2", "url-1"])


if __name__ == "__main__":
  unittest.main()
