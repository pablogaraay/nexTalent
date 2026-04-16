import json
from pathlib import Path

def read_cv_file(cv_file: str) -> str:
    path = Path(cv_file)
    if not path.exists():
        return ""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception:
            return ""
        try:
            reader = PdfReader(str(path))
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return "\n".join(text)
        except Exception:
            return ""
    return path.read_text(encoding="utf-8", errors="ignore")