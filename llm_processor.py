from dbConn import MongoManager
from config import Config
import schemas
import json

class LLMProcessor:
  
  def __init__(self, provider="ollama", model="qwen2.5:3b"):
    self.db = MongoManager()
    self.provider = provider
    self.model = model

  def prepare_batch(self,batch):
    fields_required = []
    for offer in batch:
      fields_required.append({
        "url": offer["url"],
        "title": offer["title"],
        "description": offer["description_clean"],
        "company": offer["company"],
      })
    return fields_required
    
  def build_prompts(self, json_batch):
    system_prompt = (
      "Extrae información de ofertas de empleo.\n"
      "Si un dato no aparece claramente, deja '' o [].\n\n"
      "Devuelve un único array JSON global para todo el lote.\n"
      "No devuelvas un array separado por cada oferta.\n"
      "Cada oferta debe corresponder a un único objeto dentro del mismo array final.\n\n"

      "Reglas:\n"
      "- No puede haber campos con información duplicada. Sin repeticiones dentro de una misma lista\n"
      "- Separar claramente las hard skills de las soft skills y de las herramientas.\n"
      
      "Criterios:\n"
      "- hard_skills_raw: conocimientos técnicos, metodologías, certificaciones e idiomas profesionales requeridos.\n"
      "- soft_skills_raw: competencias personales o interpersonales requeridas.\n"
      "- tools: herramientas, software, plataformas o tecnologías concretas requeridas.\n"
      "- seniority: usa solo 'practicas', 'beca', 'junior', 'mid', 'senior', 'lead', 'manager' o 'director' si hay evidencia suficiente; si no, ''.\n"
      "- work_modality: usa 'presencial', 'remoto' o 'hibrido' solo si aparece claramente; si no, ''.\n"
      "- employment_type: tipo de jornada o relación laboral solo si aparece claramente; si no, ''.\n"
    )
    user_prompt = (
      "Analiza el siguiente lote de ofertas. "
      "Devuelve un único array JSON que contenga un objeto por cada oferta del lote, "
      "conservando siempre la misma 'url' en cada resultado.\n\n"
      f"{json.dumps(json_batch, ensure_ascii=False, indent=2)}"
    )
    return system_prompt, user_prompt
  
  def call_model(self, system_prompt, user_prompt):
    if self.provider == "ollama":
      from ollama import chat
      print("\nLlamando al modelo...")
      response = chat(
        self.model,
        messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_prompt}
        ],
        stream=True,
        format=schemas.build_extraction_schema(Config.BATCH_SIZE),
        options={"temperature": 0.2}
      )
      output = ""
      for chunk in response:
        text = chunk["message"]["content"]
        print(text, end='', flush=True)
        output += text
    
    return json.loads(output)
  
  def merge_results(self, cleaned_offers, llm_results):
    merged = []
    llm_by_url = {item["url"]: item for item in llm_results}
    for offer in cleaned_offers:
      llm_offer = llm_by_url.get(offer["url"], {})
      merged.append({**offer, **llm_offer})
    return merged
  
  def process_all_batches(self, batch_size=Config.BATCH_SIZE):
    skip = 0
    while True:
      batch = self.db.load_offers_batch(Config.CLEANED_COLL, batch_size, skip)
      if not batch:
        print("No hay más ofertas para procesar.")
        break
      
      prepared_batch = self.prepare_batch(batch)
      system_prompt, user_prompt = self.build_prompts(prepared_batch)
      llm_ouput = self.call_model(system_prompt, user_prompt)
      merged_offers = self.merge_results(batch, llm_ouput)
      self.db.upsert_bulk_offers_llm(Config.LLM_RAW_COLL, merged_offers)
      skip += batch_size
  
if __name__ == "__main__":
  processor = LLMProcessor()
  processor.process_all_batches(batch_size=Config.BATCH_SIZE)