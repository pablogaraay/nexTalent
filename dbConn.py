from config import Config
from pymongo import MongoClient
from pymongo.server_api import ServerApi

class MongoManager:
  def __init__(self):
    self.client = MongoClient(Config.MONGO_URI, server_api=ServerApi(version='1'))
    self.db = self.client[Config.DB_NAME]

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
