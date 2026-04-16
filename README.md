# nexTalent

Sistema de análisis de ofertas con pipeline de scraping/LLM/mapping y orquestación multiagente con LangGraph.

## Caso de uso activo

1. Búsqueda avanzada de empleo por perfil (prompt o CV).

## Ejecución

```bash
python3 multiagent_cli.py --help
```

Ejemplo:

```bash
python3 multiagent_cli.py --profile-text "Rol: data engineer; skills: python, sql, spark"
```

También puedes pasar un CV:

```bash
python3 multiagent_cli.py --cv-file /ruta/mi_cv.pdf
```

## Web React (nuevo)

Se ha añadido una app web en `/Users/pablo/Desktop/CEU/tfg/nexTalent/web` para el caso de uso de búsqueda avanzada.

```bash
cd /Users/pablo/Desktop/CEU/tfg/nexTalent/web
npm install
npm run dev
```

- Frontend: `http://localhost:5173`
- API puente (Node): `http://localhost:8787`
