from config import Config
from infra.embeddings import embed_text
from repositories.offer_repository import OfferRepository
from repositories.vector_store import VectorStore

JOBS_COLLECTION = Config.JOBS_CHROMA_COLLECTION
SKILLS_COLLECTION = Config.SKILLS_CHROMA_COLLECTION


def _active_taxonomy_rows(rows):
  return [row for row in (rows or []) if (row or {}).get("active", True)]


def load_taxonomy_collection(offer_repository: OfferRepository, collection_name: str):
  data = offer_repository.load_offers(collection_name, active_only=False, projection={"_id": 0})
  if not isinstance(data, list):
    raise ValueError(
      f"Formato no soportado en la coleccion {collection_name}. "
      "Se espera una lista de documentos de taxonomia."
    )
  return _active_taxonomy_rows(data)
  
def main():
  offer_repository = OfferRepository()
  try:
    jobs = load_taxonomy_collection(offer_repository, Config.WEF_JOBS_TAXONOMY_COLL)
    skills = load_taxonomy_collection(offer_repository, Config.WEF_SKILLS_TAXONOMY_COLL)
  finally:
    offer_repository.close()

  if not jobs:
    raise RuntimeError(f"No hay taxonomias activas en la coleccion '{Config.WEF_JOBS_TAXONOMY_COLL}'.")
  if not skills:
    raise RuntimeError(f"No hay taxonomias activas en la coleccion '{Config.WEF_SKILLS_TAXONOMY_COLL}'.")

  jobs_ids, jobs_docs, jobs_meta, jobs_embs = [], [], [], []
  for j in jobs:
    job_id = str(j.get("job_id", "") or "").strip()
    if not job_id:
      continue
    doc = f"occupation: {j.get('occupation','')} | job_family: {j.get('job_family','')}"
    jobs_ids.append(job_id)
    jobs_docs.append(doc)
    jobs_meta.append({
        "job_id": job_id,
        "occupation": j.get("occupation", ""),
        "job_family": j.get("job_family", ""),
        "version": str(j.get("version", ""))
    })
    jobs_embs.append(embed_text(doc))

  skills_ids, skills_docs, skills_meta, skills_embs = [], [], [], []
  for s in skills:
    skill_id = str(s.get("skill_id", "") or "").strip()
    if not skill_id:
      continue
    # Texto de embedding minimalista para reducir ruido semántico.
    doc = (
      f"name: {s.get('skill_name','')} | "
      f"cluster: {s.get('skill_cluster','')} | "
      f"family: {s.get('skill_family','')} | "
      f"description: {s.get('description','')}"
    )
    skills_ids.append(skill_id)
    skills_docs.append(doc)
    skills_meta.append({
        "skill_id": skill_id,
        "skill_name": s.get("skill_name", ""),
        "skill_cluster": s.get("skill_cluster", ""),
        "skill_family": s.get("skill_family", "")
    })
    skills_embs.append(embed_text(doc))

  if not jobs_ids:
    raise RuntimeError(f"No hay jobs indexables en la coleccion '{Config.WEF_JOBS_TAXONOMY_COLL}'.")
  if not skills_ids:
    raise RuntimeError(f"No hay skills indexables en la coleccion '{Config.WEF_SKILLS_TAXONOMY_COLL}'.")

  vector_store = VectorStore()
  vector_store.delete_collection_if_exists(JOBS_COLLECTION)
  vector_store.delete_collection_if_exists(SKILLS_COLLECTION)

  jobs_coll = vector_store.get_or_create_collection(
    name=JOBS_COLLECTION,
    metadata={"hnsw:space": "cosine"}
  )
  skills_coll = vector_store.get_or_create_collection(
    name=SKILLS_COLLECTION,
    metadata={"hnsw:space": "cosine"}
  )

  jobs_coll.upsert(ids=jobs_ids, documents=jobs_docs, metadatas=jobs_meta, embeddings=jobs_embs)
  skills_coll.upsert(ids=skills_ids, documents=skills_docs, metadatas=skills_meta, embeddings=skills_embs)

  print(f"Chroma path: {vector_store.chroma_path}")
  print(f"Indexed jobs: {len(jobs_ids)}")
  print(f"Indexed skills: {len(skills_ids)}")
  print(f"Collection '{JOBS_COLLECTION}' count: {jobs_coll.count()}")
  print(f"Collection '{SKILLS_COLLECTION}' count: {skills_coll.count()}")

if __name__ == "__main__":
    main()
