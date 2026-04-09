from dbConn import MongoManager
from config import Config
import schemas
import json
from groq import Groq, RateLimitError
import time

class LLMProcessor:
  
  def __init__(self, provider="groq", model="openai/gpt-oss-120b"):
    self.db = MongoManager()
    self.provider = provider
    self.model = model
    self.client = Groq(api_key=Config.GROQ_API_KEY)

  def prepare_batch(self,batch):
    fields_required = []
    for offer in batch:
      fields_required.append({
        "title": offer["title"],
        "description": offer["description_clean"],
        "company": offer["company"],
      })
    return fields_required
    
  def build_prompts(self, json_batch):
    system_prompt = """
      1. CONTEXTO

      Eres un experto en extracción de información estructurada a partir de ofertas de empleo.
      Tu tarea consiste en analizar el título y la descripción de varias ofertas de trabajo y extraer determinados campos de forma precisa, consistente y sin inventar información.

      2. INSTRUCCIONES

      Debes extraer, para cada oferta del lote, los siguientes campos:

      - role_raw
      - hard_skills_raw
      - soft_skills_raw
      - tools_raw
      - seniority_raw
      - work_modality_raw
      - employment_type_raw

      Debes analizar únicamente la información contenida en el título y la descripción de cada oferta.

      Criterios de extracción:

      - role_raw: el rol principal del puesto, expresado de forma breve.

      - hard_skills_raw: conocimientos técnicos, metodologías, certificaciones, técnicas e idiomas profesionales requeridos.
        No incluyas aquí software, plataformas, librerías o herramientas concretas si deben ir en tools_raw.

      - soft_skills_raw: competencias personales o interpersonales requeridas.

      - tools_raw: herramientas, software, plataformas, frameworks, librerías o tecnologías concretas requeridas.

      - seniority_raw: usa solo uno de estos valores si hay evidencia suficiente:
        'practicas', 'beca', 'junior', 'mid', 'senior', 'lead', 'manager', 'director'
        Si no hay evidencia clara, devuelve ''.

      - work_modality_raw: usa solo 'presencial', 'remoto' o 'hibrido' si aparece claramente.
        Si no aparece de forma clara, devuelve ''.

      - employment_type_raw: indica el tipo de jornada o relación laboral solo si aparece claramente.
        Si no aparece de forma clara, devuelve ''.

      3. FORMATO DE SALIDA

      Devuelve únicamente un objeto JSON válido con esta estructura exacta:

      {
        "ofertas": [
          {
            "role_raw": "",
            "hard_skills_raw": [],
            "soft_skills_raw": [],
            "tools_raw": [],
            "seniority_raw": "",
            "work_modality_raw": "",
            "employment_type_raw": ""
          }
        ]
      }

      Reglas del formato:
      - La raíz debe ser un objeto JSON, no un array.
      - La clave principal debe ser exactamente "ofertas".
      - El valor de "ofertas" debe ser un array con un objeto por cada oferta del lote.
      - No devuelvas texto adicional.
      - No devuelvas explicaciones.
      - No devuelvas comentarios.
      - No devuelvas markdown.
      - No devuelvas bloques de código.

      4. EJEMPLOS

      Ejemplo 1

      Input:
      Título: Data Analyst Junior
      Descripción: Buscamos perfil con experiencia en SQL, Power BI y Excel. Se valorará capacidad analítica, comunicación y trabajo en equipo. Modalidad híbrida. Contrato indefinido.

      Output:
      {
        "ofertas": [
          {
            "role_raw": "data analyst",
            "hard_skills_raw": ["SQL"],
            "soft_skills_raw": ["capacidad analítica", "comunicación", "trabajo en equipo"],
            "tools_raw": ["Power BI", "Excel"],
            "seniority_raw": "junior",
            "work_modality_raw": "hibrido",
            "employment_type_raw": "contrato indefinido"
          }
        ]
      }

      Ejemplo 2

      Input:
      Título: Machine Learning Engineer
      Descripción: Se requiere experiencia con Python, TensorFlow, MLOps y despliegue de modelos. Se valorará autonomía y proactividad.

      Output:
      {
        "ofertas": [
          {
            "role_raw": "machine learning engineer",
            "hard_skills_raw": ["Python", "MLOps", "despliegue de modelos"],
            "soft_skills_raw": ["autonomía", "proactividad"],
            "tools_raw": ["TensorFlow"],
            "seniority_raw": "",
            "work_modality_raw": "",
            "employment_type_raw": ""
          }
        ]
      }

      5. RESTRICCIONES

      - Si un dato no aparece claramente, deja '' o [] según corresponda.
      - No inventes información.
      - No deduzcas seniority, modalidad o tipo de contrato si no hay evidencia suficiente.
      - No repitas elementos dentro de una misma lista.
      - No puede haber información duplicada entre campos si pertenece claramente a otra categoría.
      - Separa claramente hard_skills_raw, soft_skills_raw y tools_raw.
      - Cada oferta debe aparecer una sola vez dentro de "ofertas".
      - Devuelve los resultados en el mismo orden en que llegan las ofertas en la entrada.

      Ahora procesa el lote de ofertas que se proporciona a continuación.
      """

    user_prompt = (
      "Analiza el siguiente lote de ofertas. "
      "Devuelve un único objeto JSON con la clave 'ofertas', "
      "donde 'ofertas' sea un array con un objeto por cada oferta del lote. "
      "Devuelve los objetos en el mismo orden de las ofertas de entrada.\n\n"
      f"{json.dumps(json_batch, ensure_ascii=False, indent=2)}"
    )
    return system_prompt, user_prompt
  
  def call_model(self, system_prompt, user_prompt, retries=3):
    print(f"\nLlamando al modelo {self.provider} - {self.model}...")
    output_schema = schemas.build_extraction_schema()

    for attempt in range(retries):
      try:
        response = self.client.chat.completions.create(
          model = self.model,
          messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
          ],
          stream = False,
          temperature=0.0,
          #max_completion_tokens=4000,
          response_format = {
            "type": "json_schema",
            "json_schema": {
              "name": "job_offers_extraction",
              "strict": True,
              "schema": output_schema
            }
          }
        )
        print(f"Prompt tokens: {response.usage.prompt_tokens}")
        print(f"Completion tokens: {response.usage.completion_tokens}")
        output = response.choices[0].message.content or "{}"
        print("¡Extracción completada con éxito!\n")

        parsed_json = json.loads(output)
        return parsed_json.get("ofertas", [])

      except RateLimitError as e:
        headers = e.response.headers
        remaining_requests = headers.get('x-ratelimit-remaining-requests')
        
        if remaining_requests == '0':
            print("CUOTA DIARIA AGOTADA (RPD)")
            print("Se han consumido todas las peticiones permitidas para hoy.")
            exit(1)

        retry_after = headers.get('retry-after')
        reset_tokens = headers.get('x-ratelimit-reset-tokens')
        
        wait_time = 0
        if retry_after:
            wait_time = float(retry_after)
        elif reset_tokens:
            wait_time = float(reset_tokens.replace('s', ''))

        if wait_time > 120:
            print(f"La API solicita esperar {wait_time/60:.2f} minutos.")
            exit(1)
        
        if wait_time > 0:
            print(f"Límite por minuto. Esperando {wait_time}s... (Intento {attempt + 1}/{retries})")
            time.sleep(wait_time)
        else:
            wait_time = (attempt + 1) * 10
            print(f"Cabeceras no encontradas. Esperando {wait_time}s...")
            time.sleep(wait_time)

    return []
  
  def merge_results(self, cleaned_offers, llm_results):
    merged = []
    for i, offer in enumerate(cleaned_offers):
      llm_offer = llm_results[i] if i < len(llm_results) else {}
      merged.append({**offer, **llm_offer})
    return merged
  
  def process_all_batches(self, batch_size=Config.BATCH_SIZE):
    try:
        offers_processed = self.db.db[Config.LLM_RAW_COLL].count_documents({})
    except Exception as e:
        print(f"Error al contar documentos: {e}")
        offers_processed = 0
    
    skip = offers_processed

    if skip > 0:
        print(f"\nReanudando el proceso. Se han encontrado {skip} ofertas ya procesadas en '{Config.LLM_RAW_COLL}'.")
        print(f"Empezando lectura en origen a partir de la oferta {skip + 1}...\n")
    else:
        print(f"\nNo hay ofertas previas en '{Config.LLM_RAW_COLL}'. Empezando desde 0.\n")

    while True:
      batch = self.db.load_offers_batch(Config.CLEANED_COLL, batch_size, skip)
      if not batch:
        print("No hay más ofertas para procesar.")
        break
      
      prepared_batch = self.prepare_batch(batch)
      system_prompt, user_prompt = self.build_prompts(prepared_batch)
      llm_ouput = self.call_model(system_prompt, user_prompt)

      if llm_ouput:
        merged_offers = self.merge_results(batch, llm_ouput)
        self.db.upsert_bulk_offers_llm(Config.LLM_RAW_COLL, merged_offers)
      else:
        print(f"Lote en skip {skip} no se ha podido procesar. Se guarda el marcador del error")
        error_offers = []
        for offer in batch:
          error_offer = {
            **offer,
            "llm_error": True,
            "hard_skills_raw": [],
            "soft_skills_raw": [],
            "tools_raw": [],
            "seniority_raw": "",
            "work_modality_raw": "",
            "employment_type_raw": "",
            "role_raw": ""
          }
          error_offers.append(error_offer)
        
        self.db.upsert_bulk_offers_llm(Config.LLM_RAW_COLL, error_offers)
      skip += batch_size
      time.sleep(15)
  
if __name__ == "__main__":
  processor = LLMProcessor()
  processor.process_all_batches(batch_size=Config.BATCH_SIZE)
