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
ROLE_LIMIT = 0.60
SKILL_LIMIT = 0.60
UPSERT_BATCH_SIZE = 50

def embed_text(text):
  res = ollama.embed(
    model=EMBED_MODEL,
    input=text
  )
  return res['embeddings'][0]

def best_match(collection, text, LIMIT):
    text = (text or "").strip()
    if not text:
        return {"status": "unmapped", "top1": None}

    qv = embed_text(text)
    res = collection.query(query_embeddings=[qv], n_results=3, include=["metadatas", "distances"])
    metas = res["metadatas"][0]
    dists = res["distances"][0]

    candidates = []
    for m, d in zip(metas, dists):
        candidates.append({"metadata": m, "score": 1 - d})

    if not candidates:
        return {"status": "unmapped", "top1": None}

    top1 = candidates[0]
    if top1["score"] >= LIMIT:
        return {"status": "mapped", "top1": top1}
    return {"status": "unmapped", "top1": top1}

def unique_texts(arr):
    out, seen = [], set()
    for x in arr or []:
        t = str(x).strip().lower()
        if t and t not in seen:
            seen.add(t)
            out.append(str(x).strip())
    return out

def main():
    db = MongoManager()
    try:
        source_cursor = db.load_unprocessed_offers(Config.LLM_RAW_COLL, Config.MAPPED_COLL)

        chroma = PersistentClient(path=str(CHROMA_PATH))
        jobs_col = chroma.get_collection(Config.JOBS_CHROMA_COLLECTION)
        skills_col = chroma.get_collection(Config.SKILLS_CHROMA_COLLECTION)

        mapped_offers_batch = []
        total = 0
        persisted = 0

        for raw_offer in source_cursor:
            offer = dict(raw_offer)
            total += 1
            role_raw = offer.get("role_raw", "")
            role_map = best_match(jobs_col, role_raw, ROLE_LIMIT)

            skill_inputs = []
            skill_inputs.extend(unique_texts(offer.get("hard_skills_raw", [])))
            skill_inputs.extend(unique_texts(offer.get("soft_skills_raw", [])))
            skill_inputs.extend(unique_texts(offer.get("tools_raw", [])))
            skill_inputs = unique_texts(skill_inputs)

            skills_mapped = []
            for s in skill_inputs:
                m = best_match(skills_col, s, SKILL_LIMIT)
                if m["status"] == "mapped":
                    meta = m["top1"]["metadata"] or {}
                    skills_mapped.append({
                        "skill_id": meta.get("skill_id", ""),
                        "skill_name": meta.get("skill_name", ""),
                        "score": m["top1"]["score"],
                        "raw": s
                    })

            doc = {
                **offer
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
                db.upsert_bulk_offers(Config.MAPPED_COLL, mapped_offers_batch, "mapped")
                persisted += len(mapped_offers_batch)
                mapped_offers_batch = []

        if mapped_offers_batch:
            db.upsert_bulk_offers(Config.MAPPED_COLL, mapped_offers_batch, "mapped")
            persisted += len(mapped_offers_batch)

        if total == 0:
            print(f"No hay nuevas ofertas en {Config.LLM_RAW_COLL} pendientes de mapping.")
        else:
            print(f"Processed new offers: {total}")
            print(f"Persisted in {Config.MAPPED_COLL}: {persisted}")
    finally:
        db.close_connection()

if __name__ == "__main__":
    main()
