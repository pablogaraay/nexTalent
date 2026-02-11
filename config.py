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