from __future__ import annotations

from config import Config
from infra.embeddings import embed_text
from repositories.vector_store import VectorStore


def main():
  vector_store = VectorStore()
  jobs_col = vector_store.get_collection(Config.JOBS_CHROMA_COLLECTION)
  skills_col = vector_store.get_collection(Config.SKILLS_CHROMA_COLLECTION)

  print(f"Chroma path: {vector_store.chroma_path}")
  print(f"Embedding model: {Config.EMBED_MODEL}")

  role_query = "data engineer"
  role_vec = embed_text(role_query)
  role_res = jobs_col.query(query_embeddings=[role_vec], n_results=5, include=["metadatas", "distances"])
  print("ROLE QUERY:", role_query)
  for metadata, distance in zip(role_res["metadatas"][0], role_res["distances"][0]):
    print(metadata["job_id"], metadata["occupation"], "distance=", round(distance, 4), "score=", round(1 - distance, 4))

  skill_query = "python programming"
  skill_vec = embed_text(skill_query)
  skill_res = skills_col.query(query_embeddings=[skill_vec], n_results=5, include=["metadatas", "distances"])
  print("\nSKILL QUERY:", skill_query)
  for metadata, distance in zip(skill_res["metadatas"][0], skill_res["distances"][0]):
    print(metadata["skill_id"], metadata["skill_name"], "distance=", round(distance, 4), "score=", round(1 - distance, 4))


if __name__ == "__main__":
  main()
