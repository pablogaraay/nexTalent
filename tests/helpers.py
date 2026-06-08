import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from data_wrangler import DataWrangler


MOCK_DATA = Path(__file__).parent / "mock_data"


def load_mock_data(filename):
  return json.loads((MOCK_DATA / filename).read_text())


def create_data_wrangler():
  return object.__new__(DataWrangler)


def run_silently(function, *args):
  with redirect_stdout(StringIO()):
    return function(*args)
