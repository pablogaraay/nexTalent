def build_extraction_schema(batch_size):
    return {
        "type": "array",
        "minItems": batch_size,
        "maxItems": batch_size,
        "items": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "hard_skills_raw": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 8,
                },
                "soft_skills_raw": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 8,
                },
                "tools_raw": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 8,
                },
                "seniority_raw": {"type": "string"},
                "work_modality_raw": {"type": "string"},
                "employment_type_raw": {"type": "string"}
            },
            "required": [
                "url",
                "hard_skills_raw",
                "soft_skills_raw",
                "tools_raw",
                "seniority_raw",
                "work_modality_raw",
                "employment_type_raw"
            ]
        }
    }