#!/usr/bin/env sh
set -eu

docker compose exec api python -m rag.index_offers
