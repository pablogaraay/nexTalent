# nexTalent

nexTalent es una plataforma de análisis de ofertas de empleo que combina procesamiento de datos, enriquecimiento con LLM, mapeo taxonómico y recuperación semántica para tres casos de uso principales: búsqueda avanzada de empleo, insights de mercado y planificación de carrera.

## Casos de uso activos

1. Búsqueda avanzada de empleo por perfil.
- Entrada: texto libre y/o CV en PDF o DOCX.
- Salida: top ofertas recomendadas con ranking y skills coincidentes.

2. Insights de mercado.
- Entrada: ofertas ya procesadas.
- Salida: jobs y skills más demandados sobre datos reales.

3. Análisis de brecha y plan de carrera.
- Entrada: rol objetivo y perfil libre y/o CV en PDF o DOCX.
- Salida: preparación estimada, fortalezas, brechas priorizadas por demanda y hoja de ruta de hasta 12 semanas.
- El cálculo usa la frecuencia observada de skills SFIA en ofertas semánticamente relacionadas con el rol objetivo.
- El análisis, la preparación y el plan separan habilidades hard (`item_type=skill`) y soft (`item_type=attribute`).

4. Espacio profesional local.
- Mantiene en el navegador el perfil analizado, ofertas guardadas, feedback, planes, progreso, candidaturas y criterios de alerta.
- Conecta los casos de uso: una oferta puede abrir un análisis de brecha o un kit de candidatura, y un perfil del mercado puede convertirse en objetivo profesional.
- Incluye adaptación segura del CV, borrador editable de carta, preparación de entrevista y seguimiento de estados sin inventar experiencia.
- En esta fase no existe autenticación ni sincronización entre dispositivos; los datos personales se guardan en `localStorage` y pueden eliminarse desde la aplicación.

## Privacidad del perfil y CV

- Los CV admitidos son PDF o DOCX con un máximo de 10 MB.
- El fichero temporal de la API se elimina al finalizar la petición.
- El texto del perfil se procesa con el proveedor LLM configurado (Groq en la configuración actual) y los embeddings se generan con Ollama.
- La aplicación solicita consentimiento antes de enviar un CV y ofrece una página para revisar y eliminar los datos locales.

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
- Clave de Groq con cuota disponible (para parseo de perfiles con LLM)

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

## Configuración local (`.env`)

La plantilla `.env.example` está destinada al despliegue local con Docker Compose.
El quickstart la copia como `.env` en la raíz del proyecto. Su contenido
configurable es:

```env
MONGO_URI=mongodb://mongo:27017/nexTalent
GROQ_API_KEY=
AUTONOMOUS_AGENT_VERBOSE=true
VITE_API_URL=
```

- `GROQ_API_KEY` puede quedar vacía si no se utilizan las funciones que llaman al LLM.
- `AUTONOMOUS_AGENT_VERBOSE` controla los logs de decisión del planificador.
- Un `VITE_API_URL` vacío se resuelve en Docker Compose como `http://localhost:8787`.
- MongoDB, Ollama y Chroma se ejecutan dentro del stack. Chroma usa el volumen persistente `chroma_data`.

La configuración cloud no se carga desde este fichero. `.env.cloud.example` mantiene
el inventario de variables que deben configurarse por separado en Cloud Run y en
los secretos de GitHub Actions. No contiene credenciales ni direcciones reales.

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
2. `LLM + Taxonomy + Mapping` (`llm_processor.py -> rag/index_taxonomy.py -> rag/index_technology_taxonomy.py -> rag/map_offers.py`), con cron `0 5 */2 * *` en UTC.

En el segundo workflow, `llm_processor.py` puede fallar (por cuota/tokens) y aun así se ejecutan indexado y mapping sobre lo ya procesado.
`rag.index_taxonomy` lee las taxonomías desde las colecciones Mongo `wef_jobs_taxonomy` y `sfia_skills_taxonomy`, y reconstruye las colecciones vectoriales `wef_jobs` y `sfia_skills` en Chroma.
`rag.index_technology_taxonomy` lee `onet_technologies_taxonomy` y reconstruye por separado la colección vectorial `onet_technologies`.
GitHub Actions actualiza MongoDB. La base vectorial de ofertas en Chroma es un indice derivado por entorno: en local se mantiene con `data/chroma` y en cloud debe reindexarse desde GCP/VM ejecutando `python3 -m rag.index_offers` contra el Chroma correspondiente.

### Taxonomía de tecnologías

`onet_technologies_taxonomy` se mantiene separada de SFIA: contiene software, plataformas,
frameworks, librerías, lenguajes y herramientas, pero no competencias profesionales
ni atributos conductuales. El artefacto versionado se regenera desde O*NET con:

```bash
python3 scripts/build_technology_taxonomy.py /ruta/software_skills.json \
  --output nexTalent.technology_skills.json
```

El JSON resultante es un array compacto importable en la colección Mongo
`onet_technologies_taxonomy`. Cada documento contiene únicamente `technology_id`,
`preferred_label`, `aliases` y `category_id`. La procedencia global de esta
taxonomía es O*NET Software Skills 30.4 y se mantiene fuera de los documentos.
Después de importarlo, su índice vectorial se reconstruye con:

```bash
python3 -m rag.index_technology_taxonomy
```

Las métricas O*NET y las ocupaciones asociadas no forman parte de la colección
operativa. Si se necesitan para auditoría, pueden exportarse por separado con
`--evidence-output`. Los indicadores `hot` e `in_demand` se consideran evidencia
del mercado estadounidense, no demanda directa del mercado español.

Durante el mapping, las competencias profesionales y conductuales se normalizan
contra SFIA, mientras que las herramientas y tecnologías se normalizan contra
O*NET y se guardan en `technologies_onet`. El matching tecnológico prioriza
etiquetas y alias exactos; solo acepta coincidencias semánticas con umbral alto y
margen suficiente para evitar asignaciones forzadas. Para datos históricos, también
se comprueban coincidencias tecnológicas exactas que el LLM hubiera clasificado
anteriormente como hard skills.

Después de importar o modificar la taxonomía se debe remapear y reindexar:

```bash
python3 -m rag.index_technology_taxonomy
python3 -m rag.map_offers --refresh-all
python3 -m rag.index_offers
```

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

Estas variables están recogidas en `.env.cloud.example`. La plantilla es una
referencia: deben configurarse directamente en el Cloud Run Job y no copiarse como
un fichero de entorno dentro de la imagen.

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

El frontend debe definir `VITE_API_URL` con la URL pública de FastAPI. La API
permite `nextalent.info` y `www.nextalent.info` como orígenes de producción.

Resumen de configuración cloud:

- Cloud Run Web: `VITE_API_URL`.
- Cloud Run API: `MONGO_URI`, `GROQ_API_KEY`, `OLLAMA_HOST`, `CHROMA_HOST`,
  `CHROMA_PORT` y `CHROMA_SSL`.
- Cloud Run Job de indexado: `MONGO_URI`, `OLLAMA_HOST` y `CHROMA_*`.
- GitHub Actions: `MONGO_URI` y `GROQ_API_KEY` como secretos. El workflow de
  mapping define su propio `OLLAMA_HOST` porque levanta Ollama en el runner.
- `PORT` no debe declararse manualmente en Cloud Run; la plataforma lo inyecta.

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
- `offers` conserva el historico: las ofertas que desaparecen del ultimo scraping se marcan como inactivas.
- Las colecciones derivadas (`offers_structured`, `offers_cleaned`, `offers_llm_raw` y `offers_mapped`) contienen exclusivamente ofertas activas; el scraper elimina de ellas las ofertas que dejan de estar activas.
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

Búsqueda de empleo con CV PDF o DOCX:

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
  - `cv` (opcional, solo `.pdf` o `.docx`)
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
- `offers`: fuente e historico de ofertas activas e inactivas.
- `offers_structured`: ofertas activas estructuradas.
- `offers_cleaned`: ofertas activas limpias.
- `offers_llm_raw`: ofertas activas enriquecidas por el LLM.
- `offers_mapped`: ofertas activas mapeadas a las taxonomias.
- `wef_jobs_taxonomy`
- `sfia_skills_taxonomy`
- `onet_technologies_taxonomy`

ChromaDB:
- `wef_jobs`
- `sfia_skills`
- `onet_technologies`
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
