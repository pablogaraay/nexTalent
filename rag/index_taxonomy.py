import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
  sys.path.insert(0, str(BASE_DIR))

from config import Config
from chromadb import PersistentClient
import ollama

CHROMA_PATH = BASE_DIR / "data/chroma"
EMBED_MODEL = Config.EMBED_MODEL

JOBS_FILE = BASE_DIR / "nexTalent.wef_jobs_taxonomy.json"
SKILLS_FILE = BASE_DIR / "nexTalent.sfia_skills_taxonomy.json"
JOBS_COLLECTION = Config.JOBS_CHROMA_COLLECTION
SKILLS_COLLECTION = Config.SKILLS_CHROMA_COLLECTION

def embed_text(text):
  res = ollama.embed(
    model=EMBED_MODEL,
    input=text
  )
  return res['embeddings'][0]

def load_json(file_path):
  with open(file_path, "r", encoding="utf-8") as file:
    data = json.load(file)
    if not isinstance(data, list):
      raise ValueError(
        f"Formato no soportado en {file_path}. "
        "Se espera una lista JSON plana (taxonomía actual)."
      )
    return data
  
def main():
  if not JOBS_FILE.exists():
    raise FileNotFoundError(f"No se encuentra el fichero: {JOBS_FILE}")
  if not SKILLS_FILE.exists():
    raise FileNotFoundError(f"No se encuentra el fichero: {SKILLS_FILE}")

  client = PersistentClient(path=str(CHROMA_PATH))
  jobs_coll = client.get_or_create_collection(
    name=JOBS_COLLECTION,
    metadata={"hnsw:space": "cosine"}
  )
  skills_coll = client.get_or_create_collection(
    name=SKILLS_COLLECTION,
    metadata={"hnsw:space": "cosine"}
  )

  jobs = [x for x in load_json(JOBS_FILE) if x.get("active", True)]
  skills = [x for x in load_json(SKILLS_FILE) if x.get("active", True)]

  jobs_ids, jobs_docs, jobs_meta, jobs_embs = [], [], [], []
  for j in jobs:
    doc = f"occupation: {j.get('occupation','')} | job_family: {j.get('job_family','')}"
    jobs_ids.append(j["job_id"])
    jobs_docs.append(doc)
    jobs_meta.append({
        "job_id": j["job_id"],
        "occupation": j.get("occupation", ""),
        "job_family": j.get("job_family", ""),
        "version": str(j.get("version", ""))
    })
    jobs_embs.append(embed_text(doc))

  skills_ids, skills_docs, skills_meta, skills_embs = [], [], [], []
  for s in skills:
    # Texto de embedding minimalista para reducir ruido semántico.
    doc = (
      f"name: {s.get('skill_name','')} | "
      f"cluster: {s.get('skill_cluster','')} | "
      f"family: {s.get('skill_family','')} | "
      f"description: {s.get('description','')}"
    )
    skills_ids.append(s["skill_id"])
    skills_docs.append(doc)
    skills_meta.append({
        "skill_id": s["skill_id"],
        "skill_name": s.get("skill_name", ""),
        "skill_cluster": s.get("skill_cluster", ""),
        "skill_family": s.get("skill_family", "")
    })
    skills_embs.append(embed_text(doc))

  jobs_coll.upsert(ids=jobs_ids, documents=jobs_docs, metadatas=jobs_meta, embeddings=jobs_embs)
  skills_coll.upsert(ids=skills_ids, documents=skills_docs, metadatas=skills_meta, embeddings=skills_embs)

  print(f"Chroma path: {CHROMA_PATH}")
  print(f"Indexed jobs: {len(jobs_ids)}")
  print(f"Indexed skills: {len(skills_ids)}")
  print(f"Collection '{JOBS_COLLECTION}' count: {jobs_coll.count()}")
  print(f"Collection '{SKILLS_COLLECTION}' count: {skills_coll.count()}")

if __name__ == "__main__":
    main()
