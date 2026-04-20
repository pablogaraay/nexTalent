from typing import Iterable, List


def build_offer_extraction_schema():
  return {
    "type": "object",
    "properties": {
      "ofertas": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "hard_skills_raw": {
              "type": "array",
              "items": {"type": "string"}
            },
            "soft_skills_raw": {
              "type": "array",
              "items": {"type": "string"}
            },
            "tools_raw": {
              "type": "array",
              "items": {"type": "string"}
            },
            "seniority_raw": {"type": "string"},
            "work_modality_raw": {"type": "string"},
            "employment_type_raw": {"type": "string"},
            "role_raw": {"type": "string"}
          },
          "required": [
            "hard_skills_raw",
            "soft_skills_raw",
            "tools_raw",
            "seniority_raw",
            "work_modality_raw",
            "employment_type_raw",
            "role_raw"
          ],
          "additionalProperties": False
        }
      }
    },
    "required": ["ofertas"],
    "additionalProperties": False
  }


def build_extraction_schema():
  """Backward-compatible alias for llm_processor."""
  return build_offer_extraction_schema()


def build_profile_parse_schema(seniority_levels: Iterable[str]):
  levels: List[str] = list(seniority_levels or [])
  return {
    "type": "object",
    "properties": {
      "role": {"type": "string"},
      "skills": {"type": "array", "items": {"type": "string"}},
      "seniority_raw": {"type": "string", "enum": levels},
      "seniority_raw_targets": {
        "type": "array",
        "items": {"type": "string", "enum": levels}
      },
      "location_query": {"type": "string"},
      "location_targets": {
        "type": "array",
        "items": {"type": "string"}
      }
    },
    "required": [
      "role",
      "skills",
      "seniority_raw",
      "seniority_raw_targets",
      "location_query",
      "location_targets"
    ],
    "additionalProperties": False
  }


def build_profile_enrichment_schema(seniority_levels: Iterable[str]):
  levels: List[str] = list(seniority_levels or [])
  return {
    "type": "object",
    "properties": {
      "role": {"type": "string"},
      "role_candidates": {
        "type": "array",
        "items": {"type": "string"}
      },
      "skills": {
        "type": "array",
        "items": {"type": "string"}
      },
      "seniority_raw": {"type": "string", "enum": levels},
      "search_intent": {
        "type": "string",
        "enum": ["strict", "exploratory", "unclear"]
      },
      "location_query": {"type": "string"},
      "location_targets": {
        "type": "array",
        "items": {"type": "string"}
      }
    },
    "required": [
      "role",
      "role_candidates",
      "skills",
      "seniority_raw",
      "search_intent",
      "location_query",
      "location_targets"
    ],
    "additionalProperties": False
  }


def build_reranker_schema(top_n: int):
  safe_top_n = max(1, int(top_n))
  return {
    "type": "object",
    "properties": {
      "ranked": {
        "type": "array",
        "maxItems": safe_top_n,
        "items": {
          "type": "object",
          "properties": {
            "offer_id": {"type": "string"},
            "score": {"type": "number", "minimum": 0, "maximum": 1},
            "matched_skills": {"type": "array", "items": {"type": "string"}}
          },
          "required": ["offer_id", "score", "matched_skills"],
          "additionalProperties": False
        }
      }
    },
    "required": ["ranked"],
    "additionalProperties": False
  }

