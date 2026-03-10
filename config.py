import os
from dotenv import load_dotenv

load_dotenv()

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

  #LLM Config
  BATCH_SIZE = 3
