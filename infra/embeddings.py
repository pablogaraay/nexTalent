from __future__ import annotations
from typing import List
import ollama
from config import Config

def embed_text(text: str, model: str | None = None) -> List[float]:
  chosen_model = model or Config.EMBED_MODEL
  res = ollama.embed(
    model=chosen_model,
    input=text
  )
  return res["embeddings"][0]