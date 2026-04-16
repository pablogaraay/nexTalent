from __future__ import annotations

import argparse
import json

from multiagent import run_multiagent_flow


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Insights de mercado usando el flujo multiagente (LangGraph)."
  )
  parser.add_argument("--top-n", type=int, default=10, help="Numero de items top por ranking.")
  args = parser.parse_args()

  payload = run_multiagent_flow(
    params={
      "use_case": "market_insights",
      "top_n": max(1, min(int(args.top_n), 100))
    }
  )
  print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
  main()
