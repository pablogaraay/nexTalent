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
- Exposición por CLI y por web (React + API FastAPI).

## Stack tecnológico

- Backend: Python
- Orquestación: LangGraph
- LLM: Groq (`openai/gpt-oss-120b`)
- Embeddings: Ollama (`mxbai-embed-large:latest`)
- Base de datos documental: MongoDB
- Base vectorial: ChromaDB
- Frontend: React + Vite
- API web: FastAPI
- Cliente HTTP web: Axios
- Servidor web de producción: Nginx

## Requisitos previos

- Python 3.11+
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
# Con Docker Compose:
MONGO_URI=mongodb://mongo:27017/nexTalent

# Sin Docker (Mongo en local):
# MONGO_URI=mongodb://localhost:27017/nexTalent
GROQ_API_KEY=<tu_groq_api_key>

# Chroma local: dejar CHROMA_HOST vacío
CHROMA_HOST=
CHROMA_PORT=8000
CHROMA_SSL=false

# URL pública de FastAPI usada por el frontend
VITE_API_URL=

# Orígenes adicionales permitidos por CORS, separados por comas
CORS_ALLOWED_ORIGINS_EXTRA=
```

Variables opcionales usadas por la web:
- `API_PORT` (por defecto `8787`)
- `VITE_API_URL` (vacío usa `/api` en el mismo origen; en desarrollo Vite lo redirige a FastAPI)
- `VITE_PROXY_TARGET` (destino del proxy de desarrollo de Vite; por defecto `http://localhost:8787`)
- `CORS_ALLOWED_ORIGINS_EXTRA` (orígenes adicionales separados por comas)

Variables opcionales de Chroma:
- `CHROMA_HOST` vacío usa Chroma local persistente en `data/chroma`
- `CHROMA_HOST=<host>` usa un servidor Chroma remoto
- `CHROMA_PORT` por defecto `8000`
- `CHROMA_SSL` (`true/false`, por defecto `false`)

Variables opcionales del planificador autónomo:
- `AUTONOMOUS_AGENT_VERBOSE` (`true/false`, imprime decisión del planner en logs)

## Quickstart con Docker (Fase 1)

1. Copia la plantilla de entorno:

```bash
cp .env.example .env
```

2. Levanta el stack:

```bash
docker compose up --build -d
```

3. Descarga el modelo de embeddings dentro de Ollama (una sola vez):

```bash
docker compose exec ollama ollama pull mxbai-embed-large:latest
```

4. Sigue los logs de la API:

```bash
docker compose logs -f api
```

5. (Recomendado en primera ejecución) carga/actualiza las ofertas base:

```bash
docker compose exec api python scraper.py
docker compose exec api python data_wrangler.py
```

Servicios en local:
- Frontend: `http://localhost:5173`
- API: `http://localhost:8787`
- MongoDB: `localhost:27017`
- Ollama: `localhost:11434`

Nota:
- En Docker, el frontend se sirve en modo estático con Nginx.
- Nginx soporta las rutas SPA de React, pero no actúa como proxy inverso de FastAPI.
- El navegador llama directamente a la URL configurada en `VITE_API_URL`. Con el valor por defecto de Docker Compose usa `http://localhost:8787`.
- Durante desarrollo con Vite, las peticiones relativas a `/api` sí se redirigen a `VITE_PROXY_TARGET`.

## Pipeline de datos

### Opción A: Automático con GitHub Actions

El procesamiento periódico está separado en dos workflows:

1. `Ingesta y Data Wrangling` (`scraper.py -> data_wrangler.py`), con cron `0 1 */15 * *` en UTC.
2. `LLM + Taxonomy + Mapping` (`llm_processor.py -> rag/index_taxonomy.py -> rag/map_offers.py`), con cron `0 5 */2 * *` en UTC.

En el segundo workflow, `llm_processor.py` puede fallar (por cuota/tokens) y aun así se ejecutan indexado y mapping sobre lo ya procesado.
GitHub Actions actualiza MongoDB. La base vectorial de ofertas en Chroma es un indice derivado por entorno: en local se mantiene con `data/chroma` y en cloud debe reindexarse desde GCP/VM ejecutando `python3 -m rag.index_offers` contra el Chroma correspondiente.

### Reindexado de ofertas en Chroma

`rag.index_offers` debe ejecutarse despues de que cambie `offers_mapped` o el estado `is_active` de las ofertas. GitHub Actions no reindexa el Chroma persistente de ningun entorno; cada entorno reconstruye su indice desde Mongo.

En local con Docker Compose:

```bash
./scripts/reindex_offers_local.sh
```

Equivale a:

```bash
docker compose exec api python -m rag.index_offers
```

En cloud se utiliza un Cloud Run Job que ejecuta:

```bash
python3 -m rag.index_offers
```

Variables necesarias para reindexar el Chroma de GCP:

```env
MONGO_URI=<mongo-remoto>
OLLAMA_HOST=http://<ip-vm>:11434
CHROMA_HOST=<ip-vm>
CHROMA_PORT=8000
CHROMA_SSL=false
```

El despliegue actual conecta el Cloud Run Job con Ollama y ChromaDB ejecutados en una VM mediante su IP privada y acceso VPC. Cloud Scheduler lanza el Job con cron `0 9 */2 * *`, usando la zona horaria configurada en el propio Scheduler. El servicio Cloud Run de la API debe usar las mismas variables `OLLAMA_HOST` y `CHROMA_*` para consultar el índice generado.

Conviene programar el reindexado después del workflow de mapping. Si se necesita sincronización exacta, el Job puede dispararse explícitamente al terminar el workflow en lugar de depender solo del horario.

### Despliegue cloud actual

```text
Navegador
  -> Cloud Run (frontend React servido por Nginx)
  -> Cloud Run (API FastAPI)
     -> MongoDB remoto
     -> Groq
     -> VM de GCP
        -> Ollama
        -> ChromaDB

Cloud Scheduler
  -> Cloud Run Job
  -> reconstruye la colección `offers` en ChromaDB
```

El frontend debe definir `VITE_API_URL` con la URL pública de FastAPI. La API debe incluir el dominio del frontend en `CORS_ALLOWED_ORIGINS_EXTRA`.

### Opción B: Manual (sin scheduler)

Para una ejecución completa manual, lanzar:

```bash
python3 scraper.py
python3 data_wrangler.py
python3 llm_processor.py
python3 -m rag.index_taxonomy
python3 -m rag.map_offers
python3 -m rag.index_offers
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
python3 multiagent_cli.py --use-case insights --top-n 10
```

## Ejecución web

Para arrancar API y frontend conjuntamente, desde `web`:

```bash
cd web
npm run dev
```

Para arrancarlos por separado:

```bash
# Terminal 1, desde la raíz
python3 api.py

# Terminal 2
cd web
npm run dev:web
```

Servicios por defecto:
- Frontend: `http://localhost:5173`
- API: `http://localhost:8787`

## Endpoints web disponibles

`GET /api/health`
- Healthcheck básico.

`POST /api/search`
- `multipart/form-data`
- Campos:
  - `profileText` (opcional)
  - `cv` (opcional, solo `.pdf`)
- Requiere al menos uno de los dos.

`GET /api/insights`
- Devuelve ranking agregado de jobs y skills.
- Parámetros opcionales:
  - `topN` (`1..100`, por defecto `10`)
  - `company`
  - `city`
  - `region`
  - `seniority`
  - `jobFamily`

## Persistencia y colecciones

MongoDB (`DB_NAME = nexTalent`):
- `offers`
- `offers_structured`
- `offers_cleaned`
- `offers_llm_raw`
- `offers_mapped`

ChromaDB:
- `wef_jobs`
- `sfia_skills`
- `offers`

Sin `CHROMA_HOST`, Chroma usa persistencia local en `data/chroma`. Con `CHROMA_HOST`, tanto la API como los procesos de indexado usan el servidor Chroma remoto.

## Estructura principal del proyecto

```text
nexTalent/
  config.py
  db_conn.py
  scraper.py
  data_wrangler.py
  llm_processor.py
  api.py
  multiagent_cli.py
  infra/
  multiagent/
  rag/
  repositories/
  scripts/
  tests/
  utils/
  web/
  nexTalent.wef_jobs_taxonomy.json
  nexTalent.sfia_skills_taxonomy.json
```

## Pruebas

Desde la raíz:

```bash
make test
```

Equivale a:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Para verificar el frontend:

```bash
cd web
npm run build
```

## Licencia

Este proyecto se distribuye bajo la licencia incluida en `LICENSE`.
