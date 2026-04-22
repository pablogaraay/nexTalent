from __future__ import annotations
from groq import Groq
from config import Config

def get_groq_client() -> Groq | None:
  if not Config.GROQ_API_KEY:
    return None
  return Groq(api_key=Config.GROQ_API_KEY)