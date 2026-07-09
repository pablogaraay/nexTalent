from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

SUPPORTED_CV_EXTENSIONS = {".pdf", ".docx"}

WORD_TEXT_TAG = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
WORD_PARAGRAPH_TAG = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"


def _read_docx_text(path: Path) -> str:
    try:
        with ZipFile(path) as docx:
            document_xml = docx.read("word/document.xml")
    except Exception:
        return ""

    try:
        root = ElementTree.fromstring(document_xml)
    except Exception:
        return ""

    paragraphs = []
    for paragraph in root.iter(WORD_PARAGRAPH_TAG):
        text = "".join(node.text or "" for node in paragraph.iter(WORD_TEXT_TAG)).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)

def read_cv_file(cv_file: str) -> str:
    path = Path(cv_file)
    if not path.exists():
        return ""
    suffix = path.suffix.lower()
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
    if suffix == ".docx":
        return _read_docx_text(path)
    return ""
