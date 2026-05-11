from pymongo import MongoClient, UpdateOne
from pymongo.server_api import ServerApi
from datetime import datetime, timezone
from config import Config


class MongoManager:
  _connection_checked = False
  _indexes_created = False

  def __init__(self):
    self.client = MongoClient(Config.MONGO_URI, server_api=ServerApi(version='1'))
    self.db = self.client[Config.DB_NAME]
    if not MongoManager._connection_checked:
      self.verify_connection()
      MongoManager._connection_checked = True
    if not MongoManager._indexes_created:
      self.create_indexes()
      MongoManager._indexes_created = True

  def verify_connection(self):
    try:
      self.client.admin.command('ping')
    except Exception as e:
      raise RuntimeError(f"Servidor no disponible: {e}") from e

  def upsert_bulk_offers(self, coll: str, offers_array: list, stage_prefix: str):
    if not offers_array:
      print(f"No hay ofertas para insertar en la coleccion {coll}")
      return

    ops = []
    for offer in offers_array:
      source_id = offer.get("_id")
      offer_without_id = {k: v for k, v in offer.items() if k != "_id"}
      set_on_insert = {f"first_{stage_prefix}": datetime.now(timezone.utc)}
      if source_id is not None:
        set_on_insert["_id"] = source_id

      is_active = bool(offer_without_id.get("is_active", True))
      set_fields = {
        **offer_without_id,
        "is_active": is_active,
        "activity_status": offer_without_id.get("activity_status") or ("active" if is_active else "inactive"),
        "missing_count": int(offer_without_id.get("missing_count", 0) or 0),
        f"last_{stage_prefix}": datetime.now(timezone.utc),
      }
      update_doc = {
        "$set": set_fields,
        "$setOnInsert": set_on_insert,
      }
      if is_active:
        update_doc["$unset"] = {"inactive_at": "", "inactive_reason": "", "last_missing_at": ""}

      ops.append(
        UpdateOne(
          {"url": offer_without_id.get("url")},
          update_doc,
          upsert=True
        )
      )
    try:
      res = self.db[coll].bulk_write(ops, ordered=False)
      print(f"Se han insertado {res.upserted_count} ofertas en la coleccion {coll}")
      print(f"Se han actualizado {res.modified_count} ofertas en la coleccion {coll}")
    except Exception as e:
      print(f"Error al insertar las ofertas: {e}")

  def sync_active_urls(self, active_urls: list[str], collections: list[str]):
    active_urls = sorted({str(url or "").strip() for url in active_urls if str(url or "").strip()})
    min_urls = int(getattr(Config, "SCRAPER_ACTIVITY_SYNC_MIN_URLS", 1) or 1)

    if len(active_urls) < min_urls:
      print(
        "No se sincroniza actividad: "
        f"solo se han detectado {len(active_urls)} URLs activas "
        f"(minimo configurado: {min_urls})."
      )
      return

    now = datetime.now(timezone.utc)
    for coll in collections:
      active_res = self.db[coll].update_many(
        {"url": {"$in": active_urls}},
        {
          "$set": {
            "is_active": True,
            "activity_status": "active",
            "missing_count": 0,
            "last_seen_active_source": now,
          },
          "$unset": {"inactive_at": "", "inactive_reason": "", "last_missing_at": ""}
        }
      )
      inactive_res = self.db[coll].update_many(
        {"url": {"$nin": active_urls}},
        {
          "$set": {
            "is_active": False,
            "activity_status": "inactive",
            "inactive_at": now,
            "inactive_reason": "not_seen_in_latest_scrape",
            "last_missing_at": now,
          },
          "$inc": {"missing_count": 1}
        }
      )
      print(
        f"Actividad sincronizada en {coll}: "
        f"{active_res.modified_count} reactivadas/actualizadas, "
        f"{inactive_res.modified_count} marcadas como inactivas."
      )

  def create_indexes(self):
    try:
      self.db[Config.SCRAPED_COLL].create_index([("url", 1)], unique=True)

      self.db[Config.STRUCTURED_COLL].create_index([("url", 1)], unique=True)

      self.db[Config.CLEANED_COLL].create_index([("url", 1)], unique=True)

      self.db[Config.LLM_RAW_COLL].create_index([("url", 1)], unique=True)

      self.db[Config.MAPPED_COLL].create_index([("url", 1)], unique=True)

    except Exception as e:
      print(f"Error al crear el indice: {e}")

  def load_offers(self, coll, active_only=False):
    try:
      query = {"is_active": {"$ne": False}} if active_only else {}
      offers = list(self.db[coll].find(query))
      return offers
    except Exception as e:
      print(f"Error al cargar las ofertas: {e}")

  def load_unprocessed_offers(self, source_coll, processed_coll):
    try:
      pipeline = [
        {"$match": {"is_active": {"$ne": False}}},
        {
          "$lookup": {
            "from": processed_coll,
            "localField": "url",
            "foreignField": "url",
            "as": "processed_docs"
          }
        },
        {"$match": {"processed_docs": {"$eq": []}}},
        {"$project": {"processed_docs": 0}},
        {"$sort": {"_id": 1}}
      ]
      return self.db[source_coll].aggregate(pipeline, allowDiskUse=True)
    except Exception as e:
      print(f"Error al cargar ofertas no procesadas: {e}")
      return []

  def close_connection(self):
    self.client.close()
