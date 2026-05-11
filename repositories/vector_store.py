from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from chromadb import HttpClient, PersistentClient

from config import Config


class VectorStore:
  def __init__(self, path: str | None = None):
    base_dir = Path(__file__).resolve().parent.parent
    chroma_host = (getattr(Config, "CHROMA_HOST", "") or "").strip()
    if chroma_host:
      chroma_port = int(getattr(Config, "CHROMA_PORT", 8000) or 8000)
      chroma_ssl = bool(getattr(Config, "CHROMA_SSL", False))
      protocol = "https" if chroma_ssl else "http"
      self.chroma_path = f"{protocol}://{chroma_host}:{chroma_port}"
      self.client = HttpClient(host=chroma_host, port=chroma_port, ssl=chroma_ssl)
      return

    self.chroma_path = str(Path(path) if path else (base_dir / "data/chroma"))
    self.client = PersistentClient(path=self.chroma_path)

  def get_collection(self, name: str):
    return self.client.get_collection(name)

  def get_or_create_collection(self, name: str, metadata: Dict[str, Any] | None = None):
    if metadata is None:
      return self.client.get_or_create_collection(name=name)
    return self.client.get_or_create_collection(name=name, metadata=metadata)

  def delete_collection_if_exists(self, name: str) -> None:
    try:
      self.client.delete_collection(name=name)
      print(f"Coleccion Chroma eliminada: {name}")
    except Exception as exc:
      message = str(exc).lower()
      if "does not exist" in message or "not found" in message:
        print(f"Coleccion Chroma no existente, no se elimina: {name}")
        return
      raise RuntimeError(f"No se pudo eliminar la coleccion Chroma '{name}': {exc}") from exc

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
