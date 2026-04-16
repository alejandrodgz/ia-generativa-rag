# Desarrollo de Software para Inteligencia Artificial Generativa
## Caso de Aplicación — Módulo ADM · Evergreen

**Entrega 2 — RAG real con LLM**

---

## Equipo

| Integrante | Rol |
|---|---|
| Daniel Alejandro Garcia Zuluaica | Desarrollador |
| Juan Esteban Quintero Herrera | Desarrollador |
| Simon Ortiz Ohoa | Desarrollador |

**Institución:** Universidad — Medellín, 2025-2026

---

## Contexto del Proyecto

Asistente RAG que recomienda roles y permisos para nuevos usuarios del módulo ADM de Evergreen. Dado el cargo, módulo y tipo de participante de un usuario, el sistema recupera reglas de acceso y casos históricos similares, y un LLM razona sobre ese contexto para decidir el rol, los permisos, la confianza y la justificación.

📄 Informe técnico: [docs/informe_tecnico_rag.md](docs/informe_tecnico_rag.md)

---

## Requisitos previos

| Herramienta | Versión mínima | Para qué |
|---|---|---|
| Python | 3.12+ | Lenguaje base |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | 0.5+ | Gestión de entorno y dependencias |
| [Ollama](https://ollama.com/download) | cualquiera | LLM local (opcional, modo remote) |

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd ia-generativa-rag
```

### 2. Instalar `uv` (si no lo tienes)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reinicia la terminal o ejecuta `source ~/.bashrc` para que `uv` quede disponible.

### 3. Instalar dependencias

```bash
uv sync --extra dev
```

Esto crea automáticamente el entorno virtual en `.venv/` e instala todas las dependencias del proyecto incluyendo las de desarrollo (pytest, httpx, etc.).

### 4. Verificar la instalación

```bash
uv run --extra dev pytest tests/ -v
```

Deben pasar los 6 tests.

---

## Ejecución

### Modo mock (sin LLM externo)

El sistema toma decisiones determinísticas basadas en las reglas del dominio. Útil para desarrollo y CI.

```bash
uv run uvicorn rag_adm.main:app --app-dir src --reload
```

### Modo remote — Ollama local (recomendado para demo)

```bash
# 1. Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Descargar el modelo
ollama pull qwen2.5:7b

# 3. Arrancar el servidor con las variables de entorno
LLM_MODE=remote \
LLM_API_KEY=ollama \
LLM_BASE_URL=http://localhost:11434/v1 \
LLM_MODEL=qwen2.5:7b \
uv run uvicorn rag_adm.main:app --app-dir src --reload
```

### Modo remote — Gemini (Juan Esteban)

```bash
LLM_MODE=remote \
LLM_API_KEY=<tu-api-key-de-google-ai-studio> \
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai \
LLM_MODEL=gemini-1.5-flash \
uv run uvicorn rag_adm.main:app --app-dir src --reload
```

### Modo remote — Groq (Simon)

```bash
LLM_MODE=remote \
LLM_API_KEY=<tu-api-key-de-groq> \
LLM_BASE_URL=https://api.groq.com/openai/v1 \
LLM_MODEL=llama-3.1-8b-instant \
uv run uvicorn rag_adm.main:app --app-dir src --reload
```

> También puedes copiar `.env.example` a `.env` y definir las variables ahí.

---

## Acceso

Con el servidor corriendo, abre en el navegador:

| URL | Descripción |
|---|---|
| `http://127.0.0.1:8000` | Interfaz web del asistente |
| `http://127.0.0.1:8000/docs` | Documentación interactiva (Swagger) |
| `http://127.0.0.1:8000/health` | Estado de la API |
| `http://127.0.0.1:8000/metadata` | Metadatos del conocimiento cargado |

---

## Ejemplo de uso con curl

```bash
curl -X POST http://127.0.0.1:8000/recomendar-rol \
  -H "Content-Type: application/json" \
  -d '{
    "cargo": "Coordinador de agrocadena",
    "modulo_asignado": "ADM",
    "tipo_participante": "Productor",
    "descripcion_adicional": "Hace seguimiento operativo de etapas"
  }'
```

Respuesta esperada:

```json
{
  "rol_recomendado": "Invitado",
  "permisos_recomendados": ["ver_agrocadenas", "ver_etapas"],
  "justificacion": "Según las políticas del módulo ADM...",
  "nivel_confianza": "alto",
  "casos_similares_ref": ["CFG-ADM-002", "CFG-ADM-009", "CFG-ADM-017"]
}
```

---

## Ejecutar tests

```bash
# Todos los tests
uv run --extra dev pytest tests/ -v

# Solo un archivo
uv run --extra dev pytest tests/test_recommender.py -v
```

---

## Estructura del proyecto

```text
ia-generativa-rag/
├── data/
│   ├── catalogo_permisos.json          # 14 permisos del módulo ADM
│   ├── politicas_acceso.json           # Roles y reglas por tipo de participante
│   └── historico_configuraciones.json  # 20 casos históricos de asignación
├── docs/
│   ├── informe_tecnico_rag.md          # Informe Entrega 1
│   └── plan_entrega2.md                # Plan de implementación Entrega 2
├── src/rag_adm/
│   ├── main.py           # API FastAPI + interfaz web
│   ├── models.py         # Contratos de entrada y salida (Pydantic)
│   ├── knowledge_base.py # Carga los archivos JSON de data/
│   ├── retriever.py      # Interfaz Retriever + JaccardRetriever
│   ├── recommender.py    # Orquestador del flujo RAG
│   ├── prompt_builder.py # Construcción del prompt para el LLM
│   ├── llm_client.py     # MockLLMClient y RemoteLLMClient
│   ├── llm_parser.py     # Parser y validador de respuesta JSON del LLM
│   ├── settings.py       # Variables de entorno
│   └── static/
│       └── index.html    # Interfaz web
├── tests/
│   ├── test_api.py
│   └── test_recommender.py
├── pyproject.toml
└── .env.example
```

---

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `LLM_MODE` | `mock` | `mock` o `remote` |
| `LLM_API_KEY` | — | API key del proveedor LLM |
| `LLM_BASE_URL` | — | URL base compatible con OpenAI |
| `LLM_MODEL` | — | Nombre del modelo a usar |
| `LLM_TIMEOUT_SECONDS` | `20` | Timeout de la llamada al LLM |

---

## Endpoints

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | `GET` | Interfaz web |
| `/health` | `GET` | Estado de la API |
| `/metadata` | `GET` | Roles, módulos, permisos y modo LLM activo |
| `/recomendar-rol` | `POST` | Genera recomendación de rol y permisos |


---

