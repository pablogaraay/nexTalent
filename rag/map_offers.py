import argparse
from collections import Counter

from config import Config
from infra.embeddings import embed_text
from repositories.offer_repository import OfferRepository
from repositories.vector_store import VectorStore
from utils.text import normalize_text, unique_keep_order

ROLE_LIMIT = 0.60
HARD_SKILL_LIMIT = 0.78
SOFT_SKILL_LIMIT = 0.72
SKILL_STRONG_SCORE = 0.82
SKILL_MIN_MARGIN = 0.03
SKILL_QUERY_RESULTS = 25
UPSERT_BATCH_SIZE = 50


def build_exact_skill_index(collection):
  result = collection.get(include=["metadatas"])
  exact_index = {}
  for metadata in result.get("metadatas", []) or []:
    metadata = metadata or {}
    skill_name = normalize_text(str(metadata.get("skill_name", "") or ""))
    item_type = str(metadata.get("item_type", "") or "").strip().lower()
    if skill_name and item_type in {"skill", "attribute"}:
      exact_index[(skill_name, item_type)] = metadata
  return exact_index


def best_match(
  collection,
  text,
  limit,
  *,
  expected_item_type="",
  exact_index=None,
  min_margin=0.0,
  strong_score=1.0,
  n_results=3,
):
  text = (text or "").strip()
  if not text:
    return {"status": "unmapped", "top1": None, "candidates": [], "margin": None}

  expected_item_type = str(expected_item_type or "").strip().lower()
  exact_metadata = (exact_index or {}).get((normalize_text(text), expected_item_type))
  if exact_metadata:
    top1 = {"metadata": exact_metadata, "score": 1.0}
    return {
      "status": "mapped",
      "top1": top1,
      "candidates": [top1],
      "margin": 1.0,
      "method": "exact_name",
    }

  qv = embed_text(text)
  res = collection.query(
    query_embeddings=[qv],
    n_results=n_results,
    include=["metadatas", "distances"],
  )
  metas = res["metadatas"][0]
  dists = res["distances"][0]

  candidates = []
  for metadata, distance in zip(metas, dists):
    metadata = metadata or {}
    item_type = str(metadata.get("item_type", "") or "").strip().lower()
    if expected_item_type and item_type != expected_item_type:
      continue
    candidates.append({"metadata": metadata, "score": 1 - distance})
  candidates.sort(key=lambda item: item["score"], reverse=True)

  if not candidates:
    return {"status": "unmapped", "top1": None, "candidates": [], "margin": None}

  top1 = candidates[0]
  margin = top1["score"] - candidates[1]["score"] if len(candidates) > 1 else 1.0
  above_limit = top1["score"] >= limit
  sufficiently_distinct = margin >= min_margin or top1["score"] >= strong_score
  status = "mapped" if above_limit and sufficiently_distinct else "ambiguous" if above_limit else "unmapped"
  return {
    "status": status,
    "top1": top1,
    "candidates": candidates[:3],
    "margin": margin,
    "method": "semantic",
  }


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
    source_offers = offer_repository.load_offers(Config.LLM_RAW_COLL, active_only=True)
    print(f"Remapeo completo activado: se procesaran todas las ofertas activas de {Config.LLM_RAW_COLL}.")
  else:
    source_offers = offer_repository.load_unprocessed_offers(Config.LLM_RAW_COLL, Config.MAPPED_COLL)
    print(
      f"Mapping incremental activado: solo se procesaran ofertas de {Config.LLM_RAW_COLL} "
      f"que no existan en {Config.MAPPED_COLL}."
    )

  vector_store = VectorStore()
  jobs_col = vector_store.get_collection(Config.JOBS_CHROMA_COLLECTION)
  skills_col = vector_store.get_collection(Config.SKILLS_CHROMA_COLLECTION)
  exact_skill_index = build_exact_skill_index(skills_col)

  mapped_offers_batch = []
  total = 0
  persisted = 0
  mapping_cache = {}
  mapping_stats = Counter()

  for raw_offer in source_offers:
    offer = dict(raw_offer)
    total += 1
    role_raw = offer.get("role_raw", "")
    role_map = best_match(jobs_col, role_raw, ROLE_LIMIT)

    hard_inputs = unique_keep_order([str(x) for x in (offer.get("hard_skills_raw", []) or [])])
    soft_inputs = unique_keep_order([str(x) for x in (offer.get("soft_skills_raw", []) or [])])
    tool_inputs = unique_keep_order([str(x) for x in (offer.get("tools_raw", []) or [])])
    skill_inputs = [
      *[(skill, "hard", "skill") for skill in hard_inputs],
      *[(skill, "soft", "attribute") for skill in soft_inputs],
    ]
    mapping_stats["tools_excluded"] += len(tool_inputs)

    skills_by_id = {}
    offer_statuses = Counter()
    for skill, source_type, expected_item_type in skill_inputs:
      cache_key = (normalize_text(skill), expected_item_type)
      if cache_key not in mapping_cache:
        skill_limit = HARD_SKILL_LIMIT if expected_item_type == "skill" else SOFT_SKILL_LIMIT
        mapping_cache[cache_key] = best_match(
          skills_col,
          skill,
          skill_limit,
          expected_item_type=expected_item_type,
          exact_index=exact_skill_index,
          min_margin=SKILL_MIN_MARGIN,
          strong_score=SKILL_STRONG_SCORE,
          n_results=SKILL_QUERY_RESULTS,
        )
      skill_match = mapping_cache[cache_key]
      offer_statuses[skill_match["status"]] += 1
      mapping_stats[skill_match["status"]] += 1
      if skill_match["status"] == "mapped":
        metadata = skill_match["top1"]["metadata"] or {}
        skill_id = metadata.get("skill_id", "")
        mapped_item = {
          "skill_id": metadata.get("skill_id", ""),
          "skill_name": metadata.get("skill_name", ""),
          "item_type": metadata.get("item_type", ""),
          "score": skill_match["top1"]["score"],
          "raw": skill,
          "raw_evidence": [skill],
          "source_type": source_type,
          "mapping_method": skill_match.get("method", "semantic"),
          "margin": skill_match.get("margin"),
          "taxonomy_version": metadata.get("version", ""),
          "alternatives": [
            {
              "skill_id": (candidate.get("metadata") or {}).get("skill_id", ""),
              "skill_name": (candidate.get("metadata") or {}).get("skill_name", ""),
              "score": candidate.get("score", 0.0),
            }
            for candidate in skill_match.get("candidates", [])[1:]
          ],
        }
        existing = skills_by_id.get(skill_id)
        if existing:
          existing["raw_evidence"] = unique_keep_order([*existing["raw_evidence"], skill])
          if mapped_item["score"] > existing["score"]:
            mapped_item["raw_evidence"] = existing["raw_evidence"]
            skills_by_id[skill_id] = mapped_item
        elif skill_id:
          skills_by_id[skill_id] = mapped_item

    skills_mapped = list(skills_by_id.values())

    doc = {
      **offer,
      "job_mapping": {},
      "skills_sfia": [],
      "skill_mapping_meta": {
        "taxonomy_collection": Config.SFIA_SKILLS_TAXONOMY_COLL,
        "hard_semantic_threshold": HARD_SKILL_LIMIT,
        "soft_semantic_threshold": SOFT_SKILL_LIMIT,
        "hard_inputs": len(hard_inputs),
        "soft_inputs": len(soft_inputs),
        "tools_excluded": len(tool_inputs),
        "mapped": offer_statuses["mapped"],
        "ambiguous": offer_statuses["ambiguous"],
        "unmapped": offer_statuses["unmapped"],
      },
    }

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
    print(f"Skill mapping stats: {dict(mapping_stats)}")
    print(f"Unique skill mapping queries: {len(mapping_cache)}")


if __name__ == "__main__":
  main()
