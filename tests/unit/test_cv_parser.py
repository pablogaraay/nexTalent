import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from multiagent.cv_parser import read_cv_file


def write_minimal_docx(path: Path, paragraphs):
  document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {paragraphs_xml}
  </w:body>
</w:document>
""".format(
    paragraphs_xml="\n".join(
      f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs
    )
  )

  with ZipFile(path, "w") as docx:
    docx.writestr("word/document.xml", document_xml)


class TestCvParser(unittest.TestCase):
  def test_reads_docx_cv(self):
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
      path = Path(tmp.name)

    try:
      write_minimal_docx(path, ["Data engineer", "Python and SQL"])
      self.assertEqual(read_cv_file(str(path)), "Data engineer\nPython and SQL")
    finally:
      path.unlink(missing_ok=True)

  def test_ignores_unsupported_cv_extension(self):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as tmp:
      tmp.write("Data engineer with Python")
      path = Path(tmp.name)

    try:
      self.assertEqual(read_cv_file(str(path)), "")
    finally:
      path.unlink(missing_ok=True)
