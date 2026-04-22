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
        
      ops.append(
        UpdateOne(
          {"url": offer_without_id.get("url")},
          {
            "$set": {**offer_without_id, f"last_{stage_prefix}": datetime.now(timezone.utc)},
            "$setOnInsert": set_on_insert
          },
          upsert=True
        )
      )
    try:
      res = self.db[coll].bulk_write(ops, ordered=False)
      print(f"Se han insertado {res.upserted_count} ofertas en la coleccion {coll}")
      print(f"Se han actualizado {res.modified_count} ofertas en la coleccion {coll}")
    except Exception as e:
      print(f"Error al insertar las ofertas: {e}")

  def create_indexes(self):
    try:
      self.db[Config.SCRAPED_COLL].create_index([("url", 1)], unique=True)

      self.db[Config.STRUCTURED_COLL].create_index([("url", 1)], unique=True)

      self.db[Config.CLEANED_COLL].create_index([("url", 1)], unique=True)

      self.db[Config.LLM_RAW_COLL].create_index([("url", 1)], unique=True)

      self.db[Config.MAPPED_COLL].create_index([("url", 1)], unique=True)

    except Exception as e:
      print(f"Error al crear el indice: {e}")

  def load_offers(self, coll):
    try:
      offers = list(self.db[coll].find())
      return offers
    except Exception as e:
      print(f"Error al cargar las ofertas: {e}")

  def load_unprocessed_offers(self, source_coll, processed_coll):
    try:
      pipeline = [
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
      
