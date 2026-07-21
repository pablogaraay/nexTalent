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
  SCRAPER_ACTIVITY_SYNC_MIN_URLS = 50

  #DB Config
  MONGO_URI = os.getenv("MONGO_URI")
  DB_NAME = "nexTalent"
  SCRAPED_COLL = "offers"
  STRUCTURED_COLL = "offers_structured"
  CLEANED_COLL = "offers_cleaned"
  LLM_RAW_COLL = "offers_llm_raw"
  MAPPED_COLL = "offers_mapped"
  WEF_JOBS_TAXONOMY_COLL = "wef_jobs_taxonomy"
  SFIA_SKILLS_TAXONOMY_COLL = "sfia_skills_taxonomy"
  ONET_TECHNOLOGIES_TAXONOMY_COLL = "onet_technologies_taxonomy"

  #LLM Config
  BATCH_SIZE = 2
  GROQ_API_KEY = os.getenv("GROQ_API_KEY")
  PROFILE_LLM_MODEL = "openai/gpt-oss-120b"
  EMBED_MODEL = "mxbai-embed-large:latest"

  #RAG Config
  OFFERS_CHROMA_COLLECTION = "offers"
  JOBS_CHROMA_COLLECTION = "wef_jobs"
  SKILLS_CHROMA_COLLECTION = "sfia_skills"
  ONET_TECHNOLOGIES_CHROMA_COLLECTION = "onet_technologies"
  CHROMA_HOST = os.getenv("CHROMA_HOST", "").strip()
  CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000") or "8000")
  CHROMA_SSL = _env_bool("CHROMA_SSL", False)
  RETRIEVAL_TOP_K = 50
  VECTOR_FALLBACK_MIN_SCORE = 0.60

  # Autonomous agent planner
  AUTONOMOUS_AGENT_VERBOSE = _env_bool("AUTONOMOUS_AGENT_VERBOSE", True)

  # CORS (local by default, extensible for deployed frontend domains)
  CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://nextalent.info",
    "https://www.nextalent.info",
  ]