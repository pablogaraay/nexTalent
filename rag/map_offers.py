import argparse
from config import Config
from infra.embeddings import embed_text
from repositories.offer_repository import OfferRepository
from repositories.vector_store import VectorStore
from utils.text import unique_keep_order

ROLE_LIMIT = 0.60
SKILL_LIMIT = 0.70
UPSERT_BATCH_SIZE = 50


def best_match(collection, text, limit):
  text = (text or "").strip()
  if not text:
    return {"status": "unmapped", "top1": None}

  qv = embed_text(text)
  res = collection.query(query_embeddings=[qv], n_results=3, include=["metadatas", "distances"])
  metas = res["metadatas"][0]
  dists = res["distances"][0]

  candidates = []
  for metadata, distance in zip(metas, dists):
    candidates.append({"metadata": metadata, "score": 1 - distance})

  if not candidates:
    return {"status": "unmapped", "top1": None}

  top1 = candidates[0]
  if top1["score"] >= limit:
    return {"status": "mapped", "top1": top1}
  return {"status": "unmapped", "top1": top1}


def parse_args():
  parser = argparse.ArgumentParser(description="Map LLM-extracted offers to WEF/SFIA taxonomies.")
  parser.add_argument(
    "--refresh-all",
    action="store_true",
    help="Remapea todas las ofertas de offers_llm_raw, aunque ya existan en offers_mapped.",
  )
  return parser.parse_args()


def main():
  args = parse_args()
  offer_repository = OfferRepository()
  if args.refresh_all:
    source_offers = offer_repository.load_offers(Config.LLM_RAW_COLL, active_only=False)
    print(f"Remapeo completo activado: se procesaran todas las ofertas de {Config.LLM_RAW_COLL}.")
  else:
    source_offers = offer_repository.load_unprocessed_offers(Config.LLM_RAW_COLL, Config.MAPPED_COLL)
    print(
      f"Mapping incremental activado: solo se procesaran ofertas de {Config.LLM_RAW_COLL} "
      f"que no existan en {Config.MAPPED_COLL}."
    )

  vector_store = VectorStore()
  jobs_col = vector_store.get_collection(Config.JOBS_CHROMA_COLLECTION)
  skills_col = vector_store.get_collection(Config.SKILLS_CHROMA_COLLECTION)

  mapped_offers_batch = []
  total = 0
  persisted = 0

  for raw_offer in source_offers:
    offer = dict(raw_offer)
    total += 1
    role_raw = offer.get("role_raw", "")
    role_map = best_match(jobs_col, role_raw, ROLE_LIMIT)

    skill_inputs = []
    skill_inputs.extend(unique_keep_order([str(x) for x in (offer.get("hard_skills_raw", []) or [])]))
    skill_inputs.extend(unique_keep_order([str(x) for x in (offer.get("soft_skills_raw", []) or [])]))
    skill_inputs.extend(unique_keep_order([str(x) for x in (offer.get("tools_raw", []) or [])]))
    skill_inputs = unique_keep_order(skill_inputs)

    skills_mapped = []
    for skill in skill_inputs:
      skill_match = best_match(skills_col, skill, SKILL_LIMIT)
      if skill_match["status"] == "mapped":
        metadata = skill_match["top1"]["metadata"] or {}
        skills_mapped.append({
          "skill_id": metadata.get("skill_id", ""),
          "skill_name": metadata.get("skill_name", ""),
          "score": skill_match["top1"]["score"],
          "raw": skill
        })

    doc = {**offer, "job_mapping": {}, "skills_sfia": []}

    if role_map["status"] == "mapped" and role_map["top1"]:
      doc["job_mapping"] = {
        "job_id_wef": role_map["top1"]["metadata"]["job_id"],
        "job_family_wef": role_map["top1"]["metadata"]["job_family"],
        "score": role_map["top1"]["score"]
      }

    if skills_mapped:
      doc["skills_sfia"] = skills_mapped

    mapped_offers_batch.append(doc)

    if len(mapped_offers_batch) >= UPSERT_BATCH_SIZE:
      offer_repository.upsert_bulk_offers(Config.MAPPED_COLL, mapped_offers_batch, "mapped")
      persisted += len(mapped_offers_batch)
      mapped_offers_batch = []

  if mapped_offers_batch:
    offer_repository.upsert_bulk_offers(Config.MAPPED_COLL, mapped_offers_batch, "mapped")
    persisted += len(mapped_offers_batch)

  if total == 0:
    if args.refresh_all:
      print(f"No hay ofertas en {Config.LLM_RAW_COLL} para remapear.")
    else:
      print(f"No hay nuevas ofertas en {Config.LLM_RAW_COLL} pendientes de mapping.")
  else:
    print(f"Processed offers: {total}")
    print(f"Persisted in {Config.MAPPED_COLL}: {persisted}")


if __name__ == "__main__":
  main()
