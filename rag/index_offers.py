"""
Index mapped offers from MongoDB into ChromaDB for vector retrieval.
Each offer is embedded using Ollama (mxbai-embed-large) combining
role, skills, seniority, and company into a single searchable document.
"""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
  sys.path.insert(0, str(BASE_DIR))

import ollama
from chromadb import PersistentClient
from config import Config
from dbConn import MongoManager

CHROMA_PATH = BASE_DIR / "data/chroma"
EMBED_MODEL = Config.EMBED_MODEL
COLLECTION_NAME = Config.OFFERS_CHROMA_COLLECTION
BATCH_SIZE = 100


def embed_text(text):
  res = ollama.embed(
    model=EMBED_MODEL,
    input=text
  )
  return res['embeddings'][0]


def build_offer_document(offer):
  """Build a searchable text document from an offer's key fields."""
  parts = []

  role = (offer.get("role_raw") or "").strip()
  if role:
    parts.append(f"role: {role}")

  company = (offer.get("company") or "").strip()
  if company:
    parts.append(f"company: {company}")

  seniority = (offer.get("seniority_raw") or "").strip()
  if seniority:
    parts.append(f"seniority: {seniority}")

  city = (offer.get("city") or "").strip()
  if city:
    parts.append(f"city: {city}")

  hard = offer.get("hard_skills_raw") or []
  if hard:
    parts.append(f"hard_skills: {', '.join(hard)}")

  soft = offer.get("soft_skills_raw") or []
  if soft:
    parts.append(f"soft_skills: {', '.join(soft)}")

  tools = offer.get("tools_raw") or []
  if tools:
    parts.append(f"tools: {', '.join(tools)}")

  return " | ".join(parts) if parts else ""


def build_offer_metadata(offer):
  """Extract metadata fields to store alongside the embedding."""
  return {
    "url": offer.get("url", ""),
    "title": (offer.get("title") or "")[:200],
    "company": (offer.get("company") or "")[:100],
    "role_raw": (offer.get("role_raw") or "")[:100],
    "seniority_raw": (offer.get("seniority_raw") or "")[:50],
    "city": (offer.get("city") or "")[:100],
  }


def sanitize_id(url):
  """ChromaDB IDs can't contain certain chars. Use url as-is (it's unique)."""
  return url.strip()


def main():
  db = MongoManager()
  try:
    offers = db.load_offers(Config.MAPPED_COLL) or []
  finally:
    db.close_connection()

  if not offers:
    print(f"No hay ofertas en la coleccion '{Config.MAPPED_COLL}'. Nada que indexar.")
    return

  chroma = PersistentClient(path=str(CHROMA_PATH))
  collection = chroma.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
  )

  ids, docs, metas, embs = [], [], [], []
  skipped = 0

  for offer in offers:
    url = (offer.get("url") or "").strip()
    if not url:
      skipped += 1
      continue

    doc = build_offer_document(offer)
    if not doc:
      skipped += 1
      continue

    offer_id = sanitize_id(url)
    ids.append(offer_id)
    docs.append(doc)
    metas.append(build_offer_metadata(offer))
    embs.append(embed_text(doc))

    if len(ids) >= BATCH_SIZE:
      collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
      print(f"  Indexed batch of {len(ids)} offers...")
      ids, docs, metas, embs = [], [], [], []

  if ids:
    collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embs)

  print(f"\nChroma path: {CHROMA_PATH}")
  print(f"Collection: '{COLLECTION_NAME}'")
  print(f"Total offers indexed: {collection.count()}")
  print(f"Offers skipped (no url or empty doc): {skipped}")


if __name__ == "__main__":
  main()
