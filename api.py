from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from multiagent import run_multiagent_flow


app = FastAPI(title="nexTalent API", version="1.0.0")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=False,
  allow_methods=["*"],
  allow_headers=["*"]
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
      if ext != ".pdf":
        return JSONResponse(
          status_code=400,
          content={"error": "Solo se aceptan archivos con extensión .pdf."}
        )

      with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await cv.read()
        tmp.write(content)
        temp_cv_path = tmp.name

    if not profile_text and not temp_cv_path:
      return JSONResponse(
        status_code=400,
        content={"error": "Debes enviar al menos un prompt de perfil o un archivo CV (.pdf)."}
      )

    payload = run_multiagent_flow(
      params={
        "use_case": "search",
        "profile_text": profile_text,
        "cv_file": temp_cv_path,
        "top_n": 10
      }
    )
    return JSONResponse(status_code=200, content=payload)
  except Exception as exc:
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


@app.get("/api/insights")
def insights(
  topN: int = Query(default=10)
):
  safe_top_n = max(1, min(int(topN), 50))
  try:
    payload = run_multiagent_flow(
      params={
        "use_case": "market_insights",
        "top_n": safe_top_n
      }
    )
    return JSONResponse(status_code=200, content=payload)
  except Exception as exc:
    return JSONResponse(
      status_code=500,
      content={
        "error": "Falló la generación de insights de mercado.",
        "details": str(exc)
      }
    )


if __name__ == "__main__":
  port = int(os.getenv("API_PORT", "8787"))
  uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)

