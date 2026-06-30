from __future__ import annotations

import json
from typing import Any, Dict, List

from config import Config
from infra.embeddings import embed_text as shared_embed_text
from infra.groq_client import get_groq_client


def _require_llm(client):
  if not client:
    raise RuntimeError("No hay cliente LLM disponible. Revisa GROQ_API_KEY en el entorno.")


class LLMClientService:
  def __init__(self):
    self.llm_client = get_groq_client()

  def embed_text(self, text: str) -> List[float]:
    return shared_embed_text(text)

  def call_structured_extraction(self, system_prompt: str, user_prompt: str, schema: dict) -> Dict[str, Any]:
    _require_llm(self.llm_client)
    response = self.llm_client.chat.completions.create(
      model=Config.PROFILE_LLM_MODEL,
      messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
      ],
      temperature=0.0,
      response_format={
        "type": "json_schema",
        "json_schema": {"name": "extraction_parser", "strict": True, "schema": schema}
      }
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
