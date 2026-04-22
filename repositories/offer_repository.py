from __future__ import annotations
from typing import Dict, List, Any
from config import Config
from db_conn import MongoManager

class OfferRepository:
  def __init__(self, db: MongoManager | None = None):
    self.db = db or MongoManager()

  def close(self):
    if self.db:
      self.db.close_connection()

  def __del__(self):
    try:
      self.close()
    except Exception:
      pass

  def load_offers(self, collection: str) -> List[Dict[str, Any]]:
    return self.db.load_offers(collection) or []

  def load_mapped_offers(self) -> List[Dict[str, Any]]:
    return self.load_offers(Config.MAPPED_COLL)

  def load_unprocessed_offers(self, source_coll: str, processed_coll: str) -> List[Dict[str, Any]]:
    return list(self.db.load_unprocessed_offers(source_coll, processed_coll) or [])

  def upsert_bulk_offers(self, collection: str, offers: List[Dict[str, Any]], stage_prefix: str) -> None:
    self.db.upsert_bulk_offers(collection, offers, stage_prefix)
