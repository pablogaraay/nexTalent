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


def seconds_since(started_at):
  return f"{monotonic() - started_at:.2f}s"


def short_text(value, limit=120):
  text = str(value or "").replace("\n", " ").strip()
  return text if len(text) <= limit else f"{text[:limit - 3]}..."


def check_ollama_health():
  """Best-effort check to make remote Ollama issues visible in Cloud Run logs."""
  ollama_host = (os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
  started_at = monotonic()
  log_step(f"Comprobando Ollama: {ollama_host}/api/tags")
  try:
    with urlopen(f"{ollama_host}/api/tags", timeout=10) as response:
      body = response.read(500).decode("utf-8", errors="replace")
      log_step(
        f"Ollama responde HTTP {response.status} en {seconds_since(started_at)}. "
        f"Primeros bytes: {short_text(body, 180)}"
      )
  except URLError as exc:
    log_step(f"No se pudo conectar con Ollama en {seconds_since(started_at)}: {exc}")
  except Exception as exc:
    log_step(f"Error inesperado comprobando Ollama en {seconds_since(started_at)}: {exc}")


def flush_batch(collection, ids, docs, metas, embs, batch_number):
  batch_size = len(ids)
  started_at = monotonic()
  log_step(f"Enviando batch {batch_number} a Chroma: {batch_size} ofertas")
  collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
  log_step(f"Batch {batch_number} indexado en Chroma en {seconds_since(started_at)}")
  return batch_size


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

  normalized_technologies = [
    str((item or {}).get("preferred_label", "") or "").strip()
    for item in (offer.get("technologies_onet") or [])
    if str((item or {}).get("preferred_label", "") or "").strip()
  ]
  if normalized_technologies:
    parts.append(f"normalized_technologies: {', '.join(normalized_technologies)}")

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
  log_step(f"Modelo de embeddings: {Config.EMBED_MODEL}")
  log_step(f"Ollama host configurado: {os.getenv('OLLAMA_HOST') or 'http://localhost:11434'}")
  log_step(
    "Chroma remoto configurado: "
    f"{getattr(Config, 'CHROMA_HOST', '') or 'no'}:"
    f"{getattr(Config, 'CHROMA_PORT', '')}"
  )
  check_ollama_health()

  log_step("Inicializando repositorio Mongo.")
  load_started_at = monotonic()
  offer_repository = OfferRepository()
  log_step(f"Repositorio Mongo inicializado en {seconds_since(load_started_at)}")

  log_step(f"Cargando ofertas activas desde Mongo: {Config.MAPPED_COLL}")
  load_started_at = monotonic()
  try:
    offers = offer_repository.load_mapped_offers() or []
  finally:
    offer_repository.close()
  log_step(f"Ofertas activas cargadas: {len(offers)} en {seconds_since(load_started_at)}")

  log_step("Inicializando cliente de Chroma.")
  chroma_started_at = monotonic()
  vector_store = VectorStore()
  log_step(f"Cliente Chroma inicializado en {seconds_since(chroma_started_at)}")
  log_step(f"Chroma path/host usado: {vector_store.chroma_path}")

  log_step(f"Eliminando coleccion Chroma previa si existe: {COLLECTION_NAME}")
  delete_started_at = monotonic()
  vector_store.delete_collection_if_exists(COLLECTION_NAME)
  log_step(f"Borrado/revision de coleccion completado en {seconds_since(delete_started_at)}")

  if not offers:
    log_step(
      f"No hay ofertas activas en la coleccion '{Config.MAPPED_COLL}'. "
      f"Se ha eliminado la coleccion vectorial '{COLLECTION_NAME}' para evitar resultados obsoletos."
    )
    return

  log_step(f"Creando coleccion Chroma: {COLLECTION_NAME}")
  create_started_at = monotonic()
  collection = vector_store.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
  )
  log_step(f"Coleccion lista en {seconds_since(create_started_at)}")

  ids, docs, metas, embs = [], [], [], []
  skipped = 0
  processed = 0
  embedded = 0
  upserted = 0
  batch_number = 0
  embedding_seconds = 0.0
  upsert_seconds = 0.0
  embeddings_started_at = monotonic()

  for offer in offers:
    processed += 1
    url = (offer.get("url") or "").strip()
    if not url:
      skipped += 1
      log_step(f"Oferta saltada sin URL en posicion {processed}/{len(offers)}")
      continue

    doc = build_offer_document(offer)
    if not doc:
      skipped += 1
      log_step(f"Oferta saltada sin documento indexable: {short_text(url)}")
      continue

    offer_id = sanitize_id(url)
    ids.append(offer_id)
    docs.append(doc)
    metas.append(build_offer_metadata(offer))
    if embedded == 0 or processed <= 5 or processed % PROGRESS_EVERY == 0:
      log_step(
        f"Generando embedding {embedded + 1} para oferta {processed}/{len(offers)} | "
        f"title='{short_text(offer.get('title'), 80)}' | url='{short_text(url, 100)}'"
      )
    embed_started_at = monotonic()
    try:
      embs.append(embed_text(doc))
    except Exception as exc:
      log_step(
        f"Fallo generando embedding en oferta {processed}/{len(offers)} | "
        f"url='{short_text(url, 160)}' | error={type(exc).__name__}: {exc}"
      )
      raise
    embedding_seconds += monotonic() - embed_started_at
    embedded += 1
    if embedded == 1:
      log_step(f"Primer embedding generado en {seconds_since(embed_started_at)}")
    elif embedded % PROGRESS_EVERY == 0:
      log_step(
        f"Embeddings generados: {embedded}/{len(offers)} "
        f"(procesadas: {processed}, saltadas: {skipped}, "
        f"media embedding: {embedding_seconds / max(embedded, 1):.2f}s, "
        f"elapsed: {seconds_since(embeddings_started_at)})"
      )

    if len(ids) >= BATCH_SIZE:
      upsert_started_at = monotonic()
      batch_number += 1
      upserted += flush_batch(collection, ids, docs, metas, embs, batch_number)
      upsert_seconds += monotonic() - upsert_started_at
      ids, docs, metas, embs = [], [], [], []

  if ids:
    upsert_started_at = monotonic()
    batch_number += 1
    upserted += flush_batch(collection, ids, docs, metas, embs, batch_number)
    upsert_seconds += monotonic() - upsert_started_at

  log_step(
    f"Resumen indexado: procesadas={processed}, embeddings={embedded}, "
    f"saltadas={skipped}, upserted={upserted}, batches={batch_number}, "
    f"tiempo_embeddings={embedding_seconds:.2f}s, tiempo_chroma_upsert={upsert_seconds:.2f}s, "
    f"elapsed={seconds_since(embeddings_started_at)}"
  )

  log_step("Consultando count final de Chroma.")
  count_started_at = monotonic()
  total_indexed = collection.count()
  log_step(f"Count final recibido en {seconds_since(count_started_at)}")

  print(f"\nChroma path: {vector_store.chroma_path}", flush=True)
  print(f"Collection: '{COLLECTION_NAME}'", flush=True)
  print(f"Total offers indexed: {total_indexed}", flush=True)
  print(f"Offers skipped (no url or empty doc): {skipped}", flush=True)
  log_step(f"Finalizado en {seconds_since(started_at)}")


if __name__ == "__main__":
  main()
