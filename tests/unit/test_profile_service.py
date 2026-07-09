import unittest

from multiagent.services.profile_service import ProfileService


class FakeLLMClient:
  def embed_text(self, text):
    return [0.1, 0.2, 0.3]


class FakeJobsCollection:
  def query(self, query_embeddings, n_results, include):
    return {
      "metadatas": [[
        {"occupation": "Business Analyst"},
        {"occupation": "Data Analyst"},
      ]],
      "distances": [[0.08, 0.55]],
    }


class FakeVectorStore:
  def get_collection(self, name):
    return FakeJobsCollection()


class TestProfileServiceRoleMapping(unittest.TestCase):
  def test_groups_multiple_performed_roles_into_one_normalized_occupation(self):
    service = ProfileService(
      llm_client_service=FakeLLMClient(),
      vector_store=FakeVectorStore(),
    )

    result = service._map_performed_roles_to_jobs([
      "IT Strategy Intern",
      "Transformation Intern",
    ])

    self.assertEqual(len(result), 1)
    self.assertEqual(result[0]["occupation"], "Business Analyst")
    self.assertEqual(result[0]["source_roles"], ["IT Strategy Intern", "Transformation Intern"])


if __name__ == "__main__":
  unittest.main()
