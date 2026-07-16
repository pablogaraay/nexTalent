from __future__ import annotations

import logging
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import Config
from multiagent import run_multiagent_flow
from multiagent.cv_parser import SUPPORTED_CV_EXTENSIONS
from multiagent.services.external_insights_service import (
  ExternalInsightsService,
  RAW_INSIGHTS_REQUIRED_FIELDS,
)


logger = logging.getLogger(__name__)
app = FastAPI(title="nexTalent API", version="1.0.0")

app.add_middleware(
  CORSMiddleware,
  allow_origins=Config.CORS_ALLOWED_ORIGINS,
  allow_credentials=False,
  allow_methods=["GET", "POST", "OPTIONS"],
  allow_headers=["Content-Type", "Authorization"]
)

SUPPORTED_CV_LABEL = "PDF o DOCX"
MAX_INSIGHTS_JSON_BYTES = 10 * 1024 * 1024
MAX_CV_BYTES = 10 * 1024 * 1024
RATE_LIMIT_MESSAGE = (
  "Se ha alcanzado el límite diario del servicio de IA. "
  "No se ha podido analizar el CV en este momento. Inténtalo de nuevo más tarde."
)


def is_ai_rate_limit_error(message: str) -> bool:
  normalized = str(message or "").lower()
  return (
    "error code: 429" in normalized
    or "rate_limit" in normalized
    or "rate limit" in normalized
    or "tokens per day" in normalized
  )


@app.get("/api/health")
def health():
  return {"ok": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/search")
async def search(
  profileText: str = Form(default=""),
  cv: UploadFile | None = File(default=None)
):
  profile_text = (profileText or "").strip()
  temp_cv_path = ""

  try:
    if cv is not None:
      filename = cv.filename or ""
      ext = Path(filename).suffix.lower()
      if ext not in SUPPORTED_CV_EXTENSIONS:
        return JSONResponse(
          status_code=400,
          content={"error": "Solo se aceptan archivos con extensión .pdf o .docx."}
        )

      content = await cv.read()
      if len(content) > MAX_CV_BYTES:
        return JSONResponse(status_code=400, content={"error": "El CV supera el tamaño máximo permitido de 10 MB."})
      with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        temp_cv_path = tmp.name

    if not profile_text and not temp_cv_path:
      return JSONResponse(
        status_code=400,
        content={"error": f"Debes enviar al menos un prompt de perfil o un archivo CV ({SUPPORTED_CV_LABEL})."}
      )

    payload = run_multiagent_flow(
      params={
        "use_case": "search",
        "profile_text": profile_text,
        "cv_file": temp_cv_path,
        "top_n": 0
      }
    )
    if payload.get("error"):
      error_message = str(payload.get("error") or "")
      if is_ai_rate_limit_error(error_message):
        return JSONResponse(
          status_code=429,
          content={
            "error": RATE_LIMIT_MESSAGE,
            "details": error_message,
            "code": "ai_rate_limit_exceeded",
          }
        )
      return JSONResponse(status_code=500, content=payload)

    return JSONResponse(status_code=200, content=payload)
  except Exception as exc:
    logger.exception("Error ejecutando /api/search")
    if is_ai_rate_limit_error(str(exc)):
      return JSONResponse(
        status_code=429,
        content={
          "error": RATE_LIMIT_MESSAGE,
          "details": str(exc),
          "code": "ai_rate_limit_exceeded",
        }
      )
    return JSONResponse(
      status_code=500,
      content={
        "error": "Falló la ejecución del flujo multiagente.",
        "details": str(exc)
      }
    )
  finally:
    if temp_cv_path:
      try:
        os.remove(temp_cv_path)
      except Exception:
        pass


@app.post("/api/career-plan")
async def career_plan(
  targetRole: str = Form(default=""),
  profileText: str = Form(default=""),
  cv: UploadFile | None = File(default=None),
):
  target_role = (targetRole or "").strip()
  profile_text = (profileText or "").strip()
  temp_cv_path = ""

  try:
    if not target_role:
      return JSONResponse(status_code=400, content={"error": "Debes indicar un rol objetivo."})

    if cv is not None:
      filename = cv.filename or ""
      ext = Path(filename).suffix.lower()
      if ext not in SUPPORTED_CV_EXTENSIONS:
        return JSONResponse(
          status_code=400,
          content={"error": "Solo se aceptan archivos con extensión .pdf o .docx."},
        )
      content = await cv.read()
      if len(content) > MAX_CV_BYTES:
        return JSONResponse(status_code=400, content={"error": "El CV supera el tamaño máximo permitido de 10 MB."})
      with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        temp_cv_path = tmp.name

    if not profile_text and not temp_cv_path:
      return JSONResponse(
        status_code=400,
        content={"error": f"Debes describir tu perfil o subir un CV ({SUPPORTED_CV_LABEL})."},
      )

    payload = run_multiagent_flow(params={
      "use_case": "career",
      "target_role": target_role,
      "profile_text": profile_text,
      "cv_file": temp_cv_path,
      "top_k": 30,
    })
    if payload.get("error"):
      error_message = str(payload.get("error") or "")
      if is_ai_rate_limit_error(error_message):
        return JSONResponse(
          status_code=429,
          content={
            "error": RATE_LIMIT_MESSAGE,
            "details": error_message,
            "code": "ai_rate_limit_exceeded",
          },
        )
      return JSONResponse(status_code=500, content=payload)
    return JSONResponse(status_code=200, content=payload)
  except Exception as exc:
    logger.exception("Error ejecutando /api/career-plan")
    if is_ai_rate_limit_error(str(exc)):
      return JSONResponse(
        status_code=429,
        content={"error": RATE_LIMIT_MESSAGE, "details": str(exc), "code": "ai_rate_limit_exceeded"},
      )
    return JSONResponse(
      status_code=500,
      content={"error": "Falló la generación del plan de carrera.", "details": str(exc)},
    )
  finally:
    if temp_cv_path:
      try:
        os.remove(temp_cv_path)
      except Exception:
        pass


@app.get("/api/insights")
def insights(
  topN: int = Query(default=10),
  company: str = Query(default=""),
  city: str = Query(default=""),
  region: str = Query(default=""),
  seniority: str = Query(default=""),
  jobFamily: str = Query(default=""),
):
  safe_top_n = max(1, min(int(topN), 100))
  try:
    payload = run_multiagent_flow(
      params={
        "use_case": "insights",
        "top_n": safe_top_n,
        "company": (company or "").strip(),
        "city": (city or "").strip(),
        "region": (region or "").strip(),
        "seniority": (seniority or "").strip(),
        "job_family": (jobFamily or "").strip(),
      }
    )
    return JSONResponse(status_code=200, content=payload)
  except Exception as exc:
    logger.exception("Error ejecutando /api/insights")
    return JSONResponse(
      status_code=500,
      content={
        "error": "Falló la generación de insights de mercado.",
        "details": str(exc)
      }
    )


@app.post("/api/insights/upload-raw")
async def insights_from_raw_json(
  file: UploadFile = File(...),
  topN: int = Form(default=10),
  company: str = Form(default=""),
  city: str = Form(default=""),
  region: str = Form(default=""),
  seniority: str = Form(default=""),
  jobFamily: str = Form(default=""),
):
  filename = file.filename or ""
  if Path(filename).suffix.lower() != ".json":
    return JSONResponse(
      status_code=400,
      content={
        "error": "Solo se aceptan archivos JSON.",
        "required_fields": RAW_INSIGHTS_REQUIRED_FIELDS,
      }
    )

  try:
    raw = await file.read()
    if len(raw) > MAX_INSIGHTS_JSON_BYTES:
      return JSONResponse(
        status_code=400,
        content={
          "error": "El JSON supera el tamaño máximo permitido de 10 MB.",
          "required_fields": RAW_INSIGHTS_REQUIRED_FIELDS,
        }
      )

    raw_offers = json.loads(raw.decode("utf-8"))
    safe_top_n = max(1, min(int(topN), 100))
    result = ExternalInsightsService().use_case_insights_from_raw_json(
      raw_offers,
      top_n=safe_top_n,
      filters={
        "company": (company or "").strip(),
        "city": (city or "").strip(),
        "region": (region or "").strip(),
        "seniority": (seniority or "").strip(),
        "job_family": (jobFamily or "").strip(),
      },
    )
    return JSONResponse(
      status_code=200,
      content={
        "use_case": "insights",
        "source": "uploaded_raw_json",
        "error": None,
        "result": result,
      }
    )
  except UnicodeDecodeError:
    return JSONResponse(
      status_code=400,
      content={
        "error": "El archivo debe estar codificado en UTF-8.",
        "required_fields": RAW_INSIGHTS_REQUIRED_FIELDS,
      }
    )
  except json.JSONDecodeError:
    return JSONResponse(
      status_code=400,
      content={
        "error": "El archivo no contiene un JSON válido.",
        "required_fields": RAW_INSIGHTS_REQUIRED_FIELDS,
      }
    )
  except ValueError as exc:
    return JSONResponse(
      status_code=400,
      content={
        "error": str(exc),
        "required_fields": RAW_INSIGHTS_REQUIRED_FIELDS,
      }
    )
  except Exception as exc:
    logger.exception("Error ejecutando /api/insights/upload-raw")
    return JSONResponse(
      status_code=500,
      content={
        "error": "Falló el análisis del JSON de tendencias.",
        "details": str(exc),
        "required_fields": RAW_INSIGHTS_REQUIRED_FIELDS,
      }
    )


if __name__ == "__main__":
  port = int(os.getenv("PORT", os.getenv("API_PORT", "8787")))
  uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
