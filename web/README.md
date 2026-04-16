# Web app (React)

Interfaz web para el caso de uso activo: búsqueda avanzada de empleo (prompt/CV) usando el flujo LangGraph ya implementado en Python.

## 1) Instalar dependencias

```bash
cd web
npm install
```

## 2) Ejecutar frontend + API puente

```bash
npm run dev
```

- Frontend: http://localhost:5173
- API puente (Node): http://localhost:8787

## 3) Requisitos

- Mongo accesible con las colecciones del proyecto.
- Variables de entorno del proyecto raíz configuradas (`.env`), especialmente `GROQ_API_KEY` si quieres parseo de perfil con LLM.
- Python y dependencias del backend instaladas en el entorno donde se ejecuta `multiagent_cli.py`.

## Variables opcionales

- `API_PORT` para cambiar puerto del backend puente.
- `VITE_API_URL` si quieres que el frontend apunte a otra URL API en vez de usar proxy.
