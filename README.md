# nexTalent

nexTalent es una plataforma de análisis de ofertas de empleo que combina procesamiento de datos, enriquecimiento con LLM, mapeo taxonómico y recuperación semántica para dos casos de uso principales: búsqueda avanzada de empleo e insights de mercado.

## Casos de uso activos

1. Búsqueda avanzada de empleo por perfil.
- Entrada: texto libre y/o CV en PDF.
- Salida: top ofertas recomendadas con ranking y skills coincidentes.

2. Insights de mercado.
- Entrada: ofertas ya procesadas.
- Salida: jobs y skills más demandados sobre datos reales.

## Arquitectura funcional

- Scraping y almacenamiento inicial de ofertas en MongoDB.
- Normalización y limpieza de datos de ofertas.
- Extracción de campos estructurados mediante LLM.
- Mapeo de roles y skills contra taxonomías (WEF jobs + SFIA skills) usando embeddings.
- Indexación vectorial en ChromaDB para retrieval semántico.
- Orquestación multiagente con LangGraph para ejecutar casos de uso.
- Exposición por CLI y por web (React + API puente Node/Express).

## Stack tecnológico

- Backend: Python
- Orquestación: LangGraph
- LLM: Groq (`openai/gpt-oss-120b`)
- Embeddings: Ollama (`mxbai-embed-large:latest`)
- Base de datos documental: MongoDB
- Base vectorial: ChromaDB
- Frontend: React + Vite
- API web: Node.js + Express

## Requisitos previos

- Python 3.10+
- Node.js 18+
- MongoDB accesible
- Ollama instalado y en ejecución
- Clave de Groq con cuota disponible (para parseo/reranking LLM)

## Instalación

1. Clonar el repositorio y entrar al proyecto.

```bash
git clone <repo-url>
cd nexTalent
```

2. Crear entorno virtual e instalar dependencias Python.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Instalar dependencias web.

```bash
cd web
npm install
cd ..
```

4. Descargar modelo de embeddings en Ollama (si no está descargado).

```bash
ollama pull mxbai-embed-large:latest
```

## Configuración (`.env`)

Crear un archivo `.env` en la raíz del proyecto:

```env
MONGO_URI=<tu_mongo_uri>
GROQ_API_KEY=<tu_groq_api_key>
```

Variables opcionales usadas por la web:
- `API_PORT` (por defecto `8787`)
- `VITE_API_URL` (si quieres apuntar el frontend a una API externa)

## Pipeline de datos recomendado (primera ejecución)

Ejecutar en este orden:

```bash
python3 scraper.py
python3 dataWrangler.py
python3 llm_processor.py
python3 rag/index_taxonomy.py
python3 rag/map_offers.py
python3 rag/index_offers.py
```

Notas:
- El flujo es incremental por `url` en Mongo.
- `llm_processor.py` procesa ofertas de `offers_cleaned` no presentes en `offers_llm_raw`.
- `map_offers.py` procesa ofertas de `offers_llm_raw` no presentes en `offers_mapped`.

## Ejecución por CLI

Ayuda general:

```bash
python3 multiagent_cli.py --help
```

Búsqueda de empleo con texto:

```bash
python3 multiagent_cli.py --profile-text "Data engineer con Python y SQL en Madrid"
```

Búsqueda de empleo con CV PDF:

```bash
python3 multiagent_cli.py --cv-file /ruta/a/mi_cv.pdf
```

Insights de mercado:

```bash
python3 multiagent_cli.py --use-case market_insights --top-n 10
```

Atajo para insights:

```bash
python3 insights_cli.py --top-n 10
```

## Ejecución web

Desde la carpeta `web`:

```bash
npm run dev
```

Servicios por defecto:
- Frontend: `http://localhost:5173`
- API puente: `http://localhost:8787`

## Endpoints web disponibles

`GET /api/health`
- Healthcheck básico.

`POST /api/search`
- `multipart/form-data`
- Campos:
  - `profileText` (opcional)
  - `cv` (opcional, solo `.pdf`)
- Requiere al menos uno de los dos.

`GET /api/insights?topN=10`
- Devuelve ranking agregado de jobs y skills.

## Persistencia y colecciones

MongoDB (`DB_NAME = nexTalent`):
- `offers`
- `offers_structured`
- `offers_cleaned`
- `offers_llm_raw`
- `offers_mapped`

ChromaDB (`data/chroma`):
- `wef_jobs`
- `sfia_skills`
- `offers`

## Estructura principal del proyecto

```text
nexTalent/
  config.py
  dbConn.py
  scraper.py
  dataWrangler.py
  llm_processor.py
  multiagent_cli.py
  insights_cli.py
  multiagent/
  rag/
  web/
  nexTalent.wef_jobs_taxonomy.json
  nexTalent.sfia_skills_taxonomy.json
```

## Licencia

Este proyecto se distribuye bajo la licencia incluida en `LICENSE`.
