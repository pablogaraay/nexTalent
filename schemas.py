def build_extraction_schema():
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
