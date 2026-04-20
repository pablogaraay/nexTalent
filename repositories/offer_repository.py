from __future__ import annotations

from typing import Any, Callable, Dict, List

from config import Config
from dbConn import MongoManager


class OfferRepository:
  def _run(self, fn: Callable[[MongoManager], Any]):
    db = MongoManager()
    try:
      return fn(db)
    finally:
      db.close_connection()

  def load_offers(self, collection: str) -> List[Dict[str, Any]]:
    return self._run(lambda db: db.load_offers(collection) or [])

  def load_mapped_offers(self) -> List[Dict[str, Any]]:
    return self.load_offers(Config.MAPPED_COLL)

  def load_unprocessed_offers(self, source_coll: str, processed_coll: str) -> List[Dict[str, Any]]:
    return self._run(lambda db: list(db.load_unprocessed_offers(source_coll, processed_coll) or []))

  def upsert_bulk_offers(self, collection: str, offers: List[Dict[str, Any]], stage_prefix: str) -> None:
    self._run(lambda db: db.upsert_bulk_offers(collection, offers, stage_prefix))
