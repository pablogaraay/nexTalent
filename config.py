import os
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name, default=False):
  value = os.getenv(name)
  if value is None:
    return default
  return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
  #Scraper config
  KEYWORDS = ["Deloitte", "Accenture", "KPMG", "EY", "Capgemini", "PwC", "Indra", "NTT Data", "BCG", "Kyndryl"]
  LINKEDIN_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
  LOCATION = "Spain"

  #DB Config
  MONGO_URI = os.getenv("MONGO_URI")
  DB_NAME = "nexTalent"
  SCRAPED_COLL = "offers"
  STRUCTURED_COLL = "offers_structured"
  CLEANED_COLL = "offers_cleaned"
  LLM_RAW_COLL = "offers_llm_raw"
  MAPPED_COLL = "offers_mapped"

  #LLM Config
  BATCH_SIZE = 2
  GROQ_API_KEY = os.getenv("GROQ_API_KEY")
  PROFILE_LLM_MODEL = "openai/gpt-oss-120b"
  EMBED_MODEL = "mxbai-embed-large:latest"

  #RAG Config
  OFFERS_CHROMA_COLLECTION = "offers"
  JOBS_CHROMA_COLLECTION = "wef_jobs"
  SKILLS_CHROMA_COLLECTION = "sfia_skills"
  RETRIEVAL_TOP_K = 50
  RERANK_CANDIDATES = 15
  VECTOR_FALLBACK_MIN_SCORE = 0.60
  LLM_MIN_MATCH_SCORE = 0.20

  # Autonomous agent planner
  AUTONOMOUS_AGENT_VERBOSE = _env_bool("AUTONOMOUS_AGENT_VERBOSE", True)

  # CORS (fixed allowlist for local frontend)
  CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
  ]
