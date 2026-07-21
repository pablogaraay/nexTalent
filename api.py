import logging
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


logger = logging.getLogger(__name__)
app = FastAPI(title="nexTalent API", version="1.0.0")

app.add_middleware(
  CORSMiddleware,
  allow_origins=Config.CORS_ALLOWED_ORIGINS,
  allow_credentials=True,
  allow_methods=["GET", "POST", "OPTIONS"],
  allow_headers=["Content-Type", "Authorization"]
)

SUPPORTED_CV_LABEL = "PDF o DOCX"
MAX_CV_BYTES = 100 * 1024 * 1024
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


if __name__ == "__main__":
  port = int(os.getenv("PORT", os.getenv("API_PORT", "8787")))
  uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
