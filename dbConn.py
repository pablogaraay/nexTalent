from pymongo import MongoClient, UpdateOne
from pymongo.server_api import ServerApi
from datetime import datetime, timezone
from config import Config

class MongoManager:
  def __init__(self):
    self.client = MongoClient(Config.MONGO_URI, server_api=ServerApi(version='1'))
    self.db = self.client[Config.DB_NAME]
    self.verify_connection()
    self.create_indexes()

  def verify_connection(self):
    try:
      self.client.admin.command('ping')
      print("Ping exitoso")
    except Exception as e:
      print(f"Servidor no disponible: {e}")

  def upsert_bulk_offers_raw(self, coll, offers_array):
    ops = []
    for offer in offers_array:
      ops.append(
        UpdateOne(
          {"url": offer["url"]},
          {
            "$set": {**offer, "last_scraped": datetime.now(timezone.utc)},
            "$setOnInsert": {"first_scraped": datetime.now(timezone.utc)}
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

  def upsert_bulk_offers_structured(self, coll, offers_array):
    ops = []
    for offer in offers_array:
      ops.append(
        UpdateOne(
          {"url": offer["url"]},
          {
            "$set": {**offer, "last_updated": datetime.now(timezone.utc)},
            "$setOnInsert": {"first_structured": datetime.now(timezone.utc)}
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

  def upsert_bulk_offers_cleaned(self, coll, offers_array):
    ops = []
    for offer in offers_array:
      ops.append(
        UpdateOne(
          {"url": offer["url"]},
          {
            "$set": {**offer, "last_updated": datetime.now(timezone.utc)},
            "$setOnInsert": {"first_cleaned": datetime.now(timezone.utc)}
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
  
  def upsert_bulk_offers_llm(self, coll, offers_array):
    ops = []
    for offer in offers_array:
      ops.append(
        UpdateOne(
          {"url": offer["url"]},
          {
            "$set": {**offer, "last_llm": datetime.now(timezone.utc)},
            "$setOnInsert": {"first_llm": datetime.now(timezone.utc)}
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
      print(f"Indice URL creado exitosamente para la coleccion {Config.SCRAPED_COLL}")

      self.db[Config.STRUCTURED_COLL].create_index([("url", 1)], unique=True)
      print(f"Indice URL creado exitosamente para la coleccion {Config.STRUCTURED_COLL}")

      self.db[Config.CLEANED_COLL].create_index([("url", 1)], unique=True)
      print(f"Indice URL creado exitosamente para la coleccion {Config.CLEANED_COLL}")

    except Exception as e:
      print(f"Error al crear el indice: {e}")

  def load_offers(self, coll):
    try:
      offers = list(self.db[coll].find())
      return offers
    except Exception as e:
      print(f"Error al cargar las ofertas: {e}")

  def load_offers_batch(self, coll, batch_size, skip=0):
    try:
      batch_offers = list(self.db[coll].find().sort("_id", 1).limit(batch_size).skip(skip))
      return batch_offers
    except Exception as e:
      print(f"Error al cargar el lote de ofertas: {e}")

  def close_connection(self):
    self.client.close()
    print("Conexion cerrada")
      