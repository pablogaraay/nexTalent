from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from chromadb import PersistentClient


class VectorStore:
  def __init__(self, path: str | None = None):
    base_dir = Path(__file__).resolve().parent.parent
    self.chroma_path = Path(path) if path else (base_dir / "data/chroma")
    self.client = PersistentClient(path=str(self.chroma_path))

  def get_collection(self, name: str):
    return self.client.get_collection(name)

  def get_or_create_collection(self, name: str, metadata: Dict[str, Any] | None = None):
    if metadata is None:
      return self.client.get_or_create_collection(name=name)
    return self.client.get_or_create_collection(name=name, metadata=metadata)

  def query(
    self,
    collection_name: str,
    query_embedding: List[float],
    n_results: int,
    include: List[str] | None = None
  ) -> Dict[str, Any]:
    collection = self.get_collection(collection_name)
    query_include = include or ["metadatas", "distances"]
    return collection.query(
      query_embeddings=[query_embedding],
      n_results=n_results,
      include=query_include
    )
