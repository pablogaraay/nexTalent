from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from chromadb import PersistentClient
from config import Config
import ollama

CHROMA_PATH = BASE_DIR / "data/chroma"
EMBED_MODEL = Config.EMBED_MODEL

def embed_text(text: str):
    res = ollama.embed(
        model=EMBED_MODEL,
        input=text
    )
    return res["embeddings"][0]

def main():
    client = PersistentClient(path=str(CHROMA_PATH))
    jobs_col = client.get_collection(Config.JOBS_CHROMA_COLLECTION)
    skills_col = client.get_collection(Config.SKILLS_CHROMA_COLLECTION)

    print(f"Chroma path: {CHROMA_PATH}")
    print(f"Embedding model: {EMBED_MODEL}")

    role_query = "data engineer"
    qv = embed_text(role_query)
    res = jobs_col.query(query_embeddings=[qv], n_results=5, include=["metadatas", "distances"])
    print("ROLE QUERY:", role_query)
    for m, d in zip(res["metadatas"][0], res["distances"][0]):
        print(m["job_id"], m["occupation"], "distance=", round(d, 4), "score=", round(1 - d, 4))

    skill_query = "python programming"
    qv = embed_text(skill_query)
    res = skills_col.query(query_embeddings=[qv], n_results=5, include=["metadatas", "distances"])
    print("\nSKILL QUERY:", skill_query)
    for m, d in zip(res["metadatas"][0], res["distances"][0]):
        print(m["skill_id"], m["skill_name"], "distance=", round(d, 4), "score=", round(1 - d, 4))

if __name__ == "__main__":
    main()
