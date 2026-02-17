from config import Config
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timezone

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

  def insert_offers(self, coll, offers_array):
    try:
      self.db[coll].insert_many(offers_array)
      print(f"Se han insertado {len(offers_array)} ofertas en la coleccion {coll}")
    except Exception as e:
      print(f"Error al insertar las ofertas: {e}")

  def upsert_offers(self, coll, offers_array):
    try:
      for offer in offers_array:
        self.db[coll].update_one(
          {"url": offer["url"]},
          {
            "$set": {"last_scraped": datetime.now(timezone.utc)},
            "$setOnInsert": {**offer, "first_scraped": datetime.now(timezone.utc)}
          },
          upsert=True
        )
    except Exception as e:
      print(f"Error al actualizar las ofertas: {e}")

  def create_indexes(self):
    try:
      self.db["offers"].create_index([("url", 1)], unique=True)
      print("Indice URL creado exitosamente para la coleccion offers")
    except Exception as e:
      print(f"Error al crear el indice: {e}")
