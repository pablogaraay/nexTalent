from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from multiagent import run_multiagent_flow


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    description="Sistema multiagente (LangGraph) para busqueda avanzada de empleo"
  )
  parser.add_argument(
    "--use-case",
    default="search",
    choices=["search", "market_insights", "insights"],
    help="Caso de uso a ejecutar"
  )
  parser.add_argument("--profile-text", default="", help="Texto de perfil / prompt manual")
  parser.add_argument("--cv-file", default="", help="Ruta a CV .txt o .pdf")
  parser.add_argument("--top-n", type=int, default=10, help="Top N resultados")
  return parser


def build_params(args: argparse.Namespace) -> Dict[str, Any]:
  use_case = (args.use_case or "search").strip().lower()
  if use_case == "insights":
    use_case = "market_insights"
  return {
    "use_case": use_case,
    "profile_text": args.profile_text,
    "cv_file": args.cv_file,
    "top_n": max(1, min(int(args.top_n), 100))
  }


def main():
  parser = build_parser()
  args = parser.parse_args()
  params = build_params(args)
  payload = run_multiagent_flow(params=params)
  print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
  main()
