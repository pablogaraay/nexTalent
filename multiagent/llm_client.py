from __future__ import annotations

import json
from typing import Any, Dict, List

from groq import Groq

from config import Config
from infra.embeddings import embed_text as shared_embed_text
import schemas


def _require_llm(client):
  if not client:
    raise RuntimeError("No hay cliente LLM disponible. Revisa GROQ_API_KEY en el entorno.")


def parse_first_json_object(text: str) -> Dict[str, Any]:
  content = (text or "").strip()
  start = content.find("{")
  end = content.rfind("}")
  if start == -1 or end == -1 or end <= start:
    raise ValueError("No se encontró JSON válido en la respuesta del LLM.")
  return json.loads(content[start:end + 1])


def _strategy_tool_parameters() -> Dict[str, Any]:
  return {
    "type": "object",
    "properties": {
      "confidence": {"type": "number", "minimum": 0, "maximum": 1},
      "reasons": {
        "type": "array",
        "items": {"type": "string"},
        "maxItems": 5
      },
      "use_location_priority": {"type": "boolean"},
      "use_seniority_priority": {"type": "boolean"},
      "top_k_hint": {"type": "integer", "minimum": 5, "maximum": 200}
    },
    "required": [
      "confidence",
      "reasons",
      "use_location_priority",
      "use_seniority_priority",
      "top_k_hint"
    ],
    "additionalProperties": False
  }


class LLMClientService:
  def __init__(self):
    self.llm_client = Groq(api_key=Config.GROQ_API_KEY) if Config.GROQ_API_KEY else None

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

  def call_reranker(self, prompt_json: dict, top_n: int) -> List[Dict[str, Any]]:
    _require_llm(self.llm_client)
    schema = schemas.build_reranker_schema(int(top_n))

    try:
      response = self.llm_client.chat.completions.create(
        model=Config.PROFILE_LLM_MODEL,
        messages=[
          {"role": "system", "content": "Eres un motor de reranking final de ofertas. Responde solo con un JSON válido."},
          {"role": "user", "content": json.dumps(prompt_json, ensure_ascii=False)}
        ],
        temperature=0.0,
        response_format={
          "type": "json_schema",
          "json_schema": {"name": "reranker_output", "strict": True, "schema": schema}
        }
      )
      content = response.choices[0].message.content or ""
      return parse_first_json_object(content).get("ranked", []) or []
    except Exception as exc:
      print(f"Reranking error (schema): {exc}")

    try:
      response = self.llm_client.chat.completions.create(
        model=Config.PROFILE_LLM_MODEL,
        messages=[
          {"role": "system", "content": "Devuelve solo un JSON válido con key 'ranked'."},
          {"role": "user", "content": json.dumps(prompt_json, ensure_ascii=False)}
        ],
        temperature=0.0,
        response_format={"type": "json_object"}
      )
      content = response.choices[0].message.content or ""
      return parse_first_json_object(content).get("ranked", []) or []
    except Exception as exc:
      print(f"Reranking error (json_object): {exc}")
      return []

  def call_autonomous_strategy_tool(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    _require_llm(self.llm_client)

    parameters = _strategy_tool_parameters()
    tools = [
      {
        "type": "function",
        "function": {
          "name": "run_llm_rerank",
          "description": "Usa retrieval semántico y reranking con LLM para priorizar ofertas con mejor ajuste global.",
          "parameters": parameters,
        },
      },
      {
        "type": "function",
        "function": {
          "name": "run_vector_only",
          "description": "Usa solo recuperación vectorial sin reranking LLM cuando la información del perfil es parcial o ambigua.",
          "parameters": parameters,
        },
      },
      {
        "type": "function",
        "function": {
          "name": "run_no_match",
          "description": "No devuelve ofertas cuando no hay suficiente información útil para recomendar con calidad.",
          "parameters": parameters,
        },
      },
    ]

    try:
      response = self.llm_client.chat.completions.create(
        model=Config.PROFILE_LLM_MODEL,
        messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        tools=tools,
        tool_choice="auto",
      )

      msg = response.choices[0].message
      tool_calls = getattr(msg, "tool_calls", None) or []
      if tool_calls:
        first_call = tool_calls[0]
        function_name = (first_call.function.name or "").strip()
        raw_args = first_call.function.arguments or "{}"
        parsed_args = json.loads(raw_args)
        return {
          "tool_name": function_name,
          "arguments": parsed_args,
        }

      content = msg.content or "{}"
      payload = parse_first_json_object(content)
      return {"tool_name": "", "arguments": payload}
    except Exception as exc:
      print(f"Autonomous strategy tool-calling error: {exc}")
      return {}
