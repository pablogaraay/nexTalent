"""
Index mapped offers from MongoDB into ChromaDB for vector retrieval.
Each offer is embedded using Ollama (mxbai-embed-large) combining
role, skills, seniority, and company into a single searchable document.
"""

import os
from datetime import datetime, timezone
from time import monotonic
from urllib.error import URLError
from urllib.request import urlopen

from config import Config
from infra.embeddings import embed_text
from repositories.offer_repository import OfferRepository
from repositories.vector_store import VectorStore

COLLECTION_NAME = Config.OFFERS_CHROMA_COLLECTION
BATCH_SIZE = 100
PROGRESS_EVERY = 10


def log_step(message):
  timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
  print(f"[index_offers] {timestamp} | {message}", flush=True)


def elapsed(started_at):
  return f"{monotonic() - started_at:.2f}s"


def short_text(value, limit=120):
  text = str(value or "").replace("\n", " ").strip()
  return text if len(text) <= limit else f"{text[:limit - 3]}..."


def check_http_endpoint(name, url, timeout=10):
  started_at = monotonic()
  log_step(f"Comprobando {name}: {url}")
  try:
    with urlopen(url, timeout=timeout) as response:
      body = response.read(300).decode("utf-8", errors="replace")
      log_step(
        f"{name} responde HTTP {response.status} en {elapsed(started_at)} | "
        f"body='{short_text(body, 160)}'"
      )
      return True
  except URLError as exc:
    log_step(f"{name} no responde en {elapsed(started_at)} | error={exc}")
  except Exception as exc:
    log_step(f"Error comprobando {name} en {elapsed(started_at)} | {type(exc).__name__}: {exc}")
  return False


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
  started_at = monotonic()
  log_step("Inicio del indexado de ofertas.")
  log_step(f"Chroma collection objetivo: {COLLECTION_NAME}")
  ollama_host = (os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
  log_step(f"Modelo de embeddings: {Config.EMBED_MODEL}")
  log_step(f"Ollama host configurado: {ollama_host}")
  log_step(
    "Chroma remoto configurado: "
    f"{getattr(Config, 'CHROMA_HOST', '') or 'no'}:"
    f"{getattr(Config, 'CHROMA_PORT', '')}"
  )
  check_http_endpoint("Ollama", f"{ollama_host}/api/tags")
  if getattr(Config, "CHROMA_HOST", ""):
    protocol = "https" if getattr(Config, "CHROMA_SSL", False) else "http"
    check_http_endpoint(
      "Chroma",
      f"{protocol}://{Config.CHROMA_HOST}:{Config.CHROMA_PORT}/api/v1/heartbeat"
    )

  log_step(f"Cargando ofertas activas desde Mongo: {Config.MAPPED_COLL}")
  load_started_at = monotonic()
  try:
    offers = OfferRepository().load_mapped_offers() or []
  except Exception as exc:
    log_step(f"Fallo cargando ofertas desde Mongo | {type(exc).__name__}: {exc}")
    raise
  log_step(f"Ofertas activas cargadas: {len(offers)} en {elapsed(load_started_at)}")

  log_step("Inicializando cliente de Chroma.")
  chroma_client_started_at = monotonic()
  vector_store = VectorStore()
  log_step(f"Cliente de Chroma inicializado en {elapsed(chroma_client_started_at)}")
  log_step(f"Chroma path/host usado: {vector_store.chroma_path}")

  log_step(f"Eliminando coleccion Chroma previa si existe: {COLLECTION_NAME}")
  delete_started_at = monotonic()
  try:
    vector_store.delete_collection_if_exists(COLLECTION_NAME)
  except Exception as exc:
    log_step(f"Fallo eliminando coleccion Chroma '{COLLECTION_NAME}' | {type(exc).__name__}: {exc}")
    raise
  log_step(f"Borrado/revision de coleccion completado en {elapsed(delete_started_at)}")

  if not offers:
    print(
      f"No hay ofertas activas en la coleccion '{Config.MAPPED_COLL}'. "
      f"Se ha eliminado la coleccion vectorial '{COLLECTION_NAME}' para evitar resultados obsoletos."
    )
    return

  log_step(f"Creando coleccion Chroma: {COLLECTION_NAME}")
  create_started_at = monotonic()
  try:
    collection = vector_store.get_or_create_collection(
      name=COLLECTION_NAME,
      metadata={"hnsw:space": "cosine"}
    )
  except Exception as exc:
    log_step(f"Fallo creando coleccion Chroma '{COLLECTION_NAME}' | {type(exc).__name__}: {exc}")
    raise
  log_step(f"Coleccion lista en {elapsed(create_started_at)}")

  ids, docs, metas, embs = [], [], [], []
  skipped = 0
  processed = 0
  embedded = 0
  upserted = 0
  embedding_seconds = 0.0
  upsert_seconds = 0.0
  batch_number = 0
  embeddings_started_at = monotonic()

  for offer in offers:
    processed += 1
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
    if embedded == 0 or processed <= 5 or processed % PROGRESS_EVERY == 0:
      log_step(
        f"Generando embedding {embedded + 1} | oferta {processed}/{len(offers)} | "
        f"title='{short_text(offer.get('title'), 80)}' | url='{short_text(url, 100)}'"
      )
    embed_started_at = monotonic()
    try:
      embs.append(embed_text(doc))
    except Exception as exc:
      log_step(
        f"Fallo en embedding | oferta {processed}/{len(offers)} | "
        f"url='{short_text(url, 160)}' | {type(exc).__name__}: {exc}"
      )
      raise
    embedding_seconds += monotonic() - embed_started_at
    embedded += 1
    if embedded == 1:
      log_step(f"Primer embedding generado en {elapsed(embed_started_at)}")
    elif embedded % PROGRESS_EVERY == 0:
      log_step(
        f"Embeddings generados: {embedded}/{len(offers)} "
        f"(procesadas: {processed}, saltadas: {skipped}, "
        f"media_embedding={embedding_seconds / max(embedded, 1):.2f}s, "
        f"elapsed={elapsed(embeddings_started_at)})"
      )

    if len(ids) >= BATCH_SIZE:
      batch_number += 1
      log_step(f"Enviando batch {batch_number} a Chroma: {len(ids)} ofertas")
      upsert_started_at = monotonic()
      try:
        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
      except Exception as exc:
        log_step(f"Fallo haciendo upsert del batch {batch_number} en Chroma | {type(exc).__name__}: {exc}")
        raise
      upsert_seconds += monotonic() - upsert_started_at
      upserted += len(ids)
      log_step(
        f"Batch {batch_number} indexado: {len(ids)} ofertas en {elapsed(upsert_started_at)} "
        f"(total indexadas: {upserted})"
      )
      ids, docs, metas, embs = [], [], [], []

  if ids:
    batch_number += 1
    log_step(f"Enviando batch final {batch_number} a Chroma: {len(ids)} ofertas")
    upsert_started_at = monotonic()
    try:
      collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
    except Exception as exc:
      log_step(f"Fallo haciendo upsert del batch final {batch_number} en Chroma | {type(exc).__name__}: {exc}")
      raise
    upsert_seconds += monotonic() - upsert_started_at
    upserted += len(ids)
    log_step(
      f"Batch final {batch_number} indexado: {len(ids)} ofertas en {elapsed(upsert_started_at)} "
      f"(total indexadas: {upserted})"
    )

  log_step(
    f"Tiempo total generando embeddings y subiendo batches: {elapsed(embeddings_started_at)} | "
    f"tiempo_embeddings={embedding_seconds:.2f}s | tiempo_upsert_chroma={upsert_seconds:.2f}s"
  )

  log_step("Consultando count final en Chroma.")
  count_started_at = monotonic()
  try:
    total_indexed = collection.count()
  except Exception as exc:
    log_step(f"Fallo consultando count final de Chroma | {type(exc).__name__}: {exc}")
    raise
  log_step(f"Count final obtenido en {elapsed(count_started_at)}")

  print(f"\nChroma path: {vector_store.chroma_path}", flush=True)
  print(f"Collection: '{COLLECTION_NAME}'", flush=True)
  print(f"Total offers indexed: {total_indexed}", flush=True)
  print(f"Offers skipped (no url or empty doc): {skipped}", flush=True)
  log_step(f"Finalizado en {elapsed(started_at)}")


if __name__ == "__main__":
  main()
