"""Index the canonical onet_technologies_taxonomy Mongo collection in Chroma."""

from config import Config
from infra.embeddings import embed_text
from rag.index_taxonomy import load_taxonomy_collection
from repositories.offer_repository import OfferRepository
from repositories.vector_store import VectorStore


MIN_TECHNOLOGY_TAXONOMY_ROWS = 250
EXPECTED_TECHNOLOGY_FIELDS = {
  "technology_id", "preferred_label", "aliases", "category_id",
}


def validate_technology_taxonomy(rows):
  rows = list(rows or [])
  if len(rows) < MIN_TECHNOLOGY_TAXONOMY_ROWS:
    raise ValueError(
      "Taxonomía tecnológica incompleta: "
      f"se esperaban al menos {MIN_TECHNOLOGY_TAXONOMY_ROWS} elementos "
      f"y se encontraron {len(rows)}."
    )

  seen_ids = set()
  seen_labels = set()
  for row in rows:
    extra_fields = set(row or {}) - EXPECTED_TECHNOLOGY_FIELDS
    missing_fields = EXPECTED_TECHNOLOGY_FIELDS - set(row or {})
    if extra_fields or missing_fields:
      raise ValueError(
        "Esquema de onet_technologies_taxonomy inválido: "
        f"faltan {sorted(missing_fields)} y sobran {sorted(extra_fields)}."
      )
    technology_id = str((row or {}).get("technology_id", "") or "").strip()
    preferred_label = str((row or {}).get("preferred_label", "") or "").strip()
    category_id = str((row or {}).get("category_id", "") or "").strip()
    if not technology_id or not preferred_label or not category_id:
      raise ValueError(
        "onet_technologies_taxonomy contiene elementos sin id, etiqueta o categoría."
      )
    if technology_id in seen_ids:
      raise ValueError(f"technology_id duplicado: {technology_id}.")
    label_key = preferred_label.casefold()
    if label_key in seen_labels:
      raise ValueError(f"preferred_label duplicado: {preferred_label}.")
    seen_ids.add(technology_id)
    seen_labels.add(label_key)
  return rows


def build_embedding_document(technology):
  aliases = " | ".join(str(alias).strip() for alias in technology.get("aliases", []) if str(alias).strip())
  return (
    f"name: {technology.get('preferred_label', '')} | "
    f"aliases: {aliases} | "
    f"category: {technology.get('category_id', '')}"
  )


def main():
  repository = OfferRepository()
  try:
    technologies = validate_technology_taxonomy(
      load_taxonomy_collection(repository, Config.ONET_TECHNOLOGIES_TAXONOMY_COLL)
    )
  finally:
    repository.close()

  ids, documents, metadatas, embeddings = [], [], [], []
  for technology in technologies:
    technology_id = str(technology.get("technology_id", "") or "").strip()
    document = build_embedding_document(technology)
    aliases = " | ".join(
      str(alias).strip() for alias in technology.get("aliases", []) if str(alias).strip()
    )
    ids.append(technology_id)
    documents.append(document)
    metadatas.append({
      "technology_id": technology_id,
      "preferred_label": technology.get("preferred_label", ""),
      "aliases": aliases,
      "category_id": technology.get("category_id", ""),
    })
    embeddings.append(embed_text(document))

  vector_store = VectorStore()
  collection_name = Config.ONET_TECHNOLOGIES_CHROMA_COLLECTION
  vector_store.delete_collection_if_exists(collection_name)
  collection = vector_store.get_or_create_collection(
    name=collection_name,
    metadata={"hnsw:space": "cosine"},
  )
  collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
  print(f"Chroma path: {vector_store.chroma_path}")
  print(f"Indexed technologies: {len(ids)}")
  print(f"Collection '{collection_name}' count: {collection.count()}")


if __name__ == "__main__":
  main()
