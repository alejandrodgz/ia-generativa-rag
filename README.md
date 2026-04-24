# Asistente RAG Evergreen Multi-modulo

Prototipo de IA generativa para recomendar roles y permisos en Evergreen a partir del perfil de un usuario, con trazabilidad del contexto recuperado, soporte para multiples LLM y un analisis mock posterior de impacto de licencias y costos.

El proyecto cubre los modulos `ADM`, `DIS`, `PLA` y `FIN`, y fue construido como caso de aplicacion para el curso de Desarrollo de Software para Inteligencia Artificial Generativa.

## Equipo

| Integrante | Rol |
|---|---|
| Daniel Alejandro Garcia Zuluaica | Desarrollador |
| Juan Esteban Quintero Herrera | Desarrollador |
| Simon Ortiz Ohoa | Desarrollador |

Institucion: Universidad, Medellin, 2025-2026

## 1. Que hace el sistema

La app recibe un perfil operativo:

- `cargo`
- `modulo_asignado`
- `descripcion_adicional` opcional
- `llm_provider` opcional

Con eso ejecuta un flujo RAG:

1. recupera reglas del modulo
2. recupera casos historicos similares
3. recupera documentos extra de apoyo si existen
4. arma un prompt estructurado
5. invoca un LLM remoto o usa un fallback deterministico
6. valida la salida
7. devuelve una recomendacion explicable
8. calcula un reporte mock de impacto de licencias y costos en sistemas externos

La respuesta principal incluye:

- `rol_recomendado`
- `permisos_recomendados`
- `justificacion`
- `nivel_confianza`
- `tipo_participante_inferido`
- referencias de reglas, casos y documentos recuperados
- `retrieval_mode`
- `reranking_info` si se usa modo `hybrid`

## 2. Funcionalidades principales

- Recomendacion de rol y permisos con RAG.
- Soporte para 3 proveedores LLM: `ollama`, `huggingface` y `openai`.
- Selector de proveedor en la UI.
- Modos de retrieval `jaccard`, `vector` y `hybrid`.
- Indexacion vectorial con ChromaDB.
- Carga de documentos del usuario en `data/user_knowledge/`.
- Generacion de casos sinteticos para enriquecer el historico.
- Trazabilidad operativa del indice vectorial y de las evidencias recuperadas.
- Analisis mock de impacto de licencias, costos y areas aprobadoras.
- API REST documentada con FastAPI.

## 3. Arquitectura del proyecto

### Vista general

```text
UI estatico
   |
   v
FastAPI (main.py)
   |
   +--> metadata y estado runtime
   +--> recomendacion RAG
   +--> enrichment y reindexacion
   +--> impacto de licencias
   |
   v
RolePermissionRecommender
   |
   +--> Retriever (jaccard | vector | hybrid)
   +--> LLM Client (remote | mock fallback)
   +--> KnowledgeBase
```

### Flujo interno de recomendacion

```text
Request del usuario
   -> retriever.retrieve_rules()
   -> retriever.retrieve_similar_cases()
   -> retriever.retrieve_supporting_documents()
   -> PromptBundle
   -> RemoteLLMClient o MockLLMClient
   -> llm_parser valida JSON
   -> RecommendationResponse
```

### Flujo posterior de impacto de licencias

```text
RecommendationResponse
   -> POST /analizar-impacto-licencias
   -> politicas_licencias_costos.json
   -> evidencias vectoriales de apoyo
   -> LicenseImpactResponse
```

## 4. Mapa del codigo

### Backend principal

| Archivo | Responsabilidad |
|---|---|
| [src/rag_adm/main.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/main.py:1) | Expone endpoints FastAPI, inicializa caches, selecciona retriever y LLM |
| [src/rag_adm/models.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/models.py:1) | Schemas Pydantic de requests y responses |
| [src/rag_adm/settings.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/settings.py:1) | Lee `.env` y resuelve configuracion de proveedores y retrieval |

### Nucleo RAG

| Archivo | Responsabilidad |
|---|---|
| [src/rag_adm/knowledge_base.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/knowledge_base.py:1) | Carga politicas, catalogo de permisos e historico |
| [src/rag_adm/retriever.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/retriever.py:1) | Implementa `JaccardRetriever`, `VectorRetriever` y `HybridRetriever` |
| [src/rag_adm/recommender.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/recommender.py:1) | Orquesta retrieval + LLM + validacion de salida |
| [src/rag_adm/prompt_builder.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/prompt_builder.py:1) | Construye el prompt estructurado para el modelo |
| [src/rag_adm/llm_client.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/llm_client.py:1) | Cliente remoto compatible con OpenAI y fallback mock |
| [src/rag_adm/llm_parser.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/llm_parser.py:1) | Extrae y valida la respuesta JSON del LLM |

### Retrieval vectorial y enrichment

| Archivo | Responsabilidad |
|---|---|
| [src/rag_adm/vector_store.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/vector_store.py:1) | Construye o carga el indice Chroma persistente |
| [src/rag_adm/index_metadata.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/index_metadata.py:1) | Guarda y valida metadatos del indice |
| [src/rag_adm/enrichment.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/enrichment.py:1) | Sube documentos, genera sinteticos y administra `user_knowledge` |

### Impacto de licencias

| Archivo | Responsabilidad |
|---|---|
| [src/rag_adm/license_impact.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/license_impact.py:1) | Evalua costos, licencias, riesgos y evidencias mock |
| [data/politicas_licencias_costos.json](/home/alejandro/dev/ia-generativa-rag/data/politicas_licencias_costos.json:1) | Catalogo mock de reglas de impacto externo |
| [data/escenarios_impacto_licencias.json](/home/alejandro/dev/ia-generativa-rag/data/escenarios_impacto_licencias.json:1) | Casos esperados para pruebas de impacto |

### Frontend

| Archivo | Responsabilidad |
|---|---|
| [src/rag_adm/static/index.html](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/static/index.html:1) | UI completa: formulario, selector LLM, trazabilidad, enrichment e impacto |

## 5. Base de conocimiento

La base de conocimiento principal vive en `data/`:

- `politicas_acceso.json`: roles y reglas por modulo y tipo de participante.
- `catalogo_permisos.json`: universo valido de permisos.
- `historico_configuraciones.json`: precedentes reales o mock.
- `historico_sintetico.json`: casos generados por enrichment.
- `user_knowledge/*.txt`: documentos extra agregados por el usuario.
- `politicas_licencias_costos.json`: reglas mock de impacto externo.

El sistema no permite que el LLM invente roles o permisos fuera del catalogo, porque la salida se valida contra los datos cargados en `KnowledgeBase`.

## 6. Modos de retrieval

### `jaccard`

- No necesita indice vectorial.
- Compara tokens normalizados.
- Sirve como baseline rapido o modo sin dependencias pesadas.

### `vector`

- Usa ChromaDB y embeddings.
- Indexa reglas, permisos, historicos y documentos extra.
- Recupera reglas, casos y documentos por similitud semantica.

### `hybrid`

- Usa reglas estructuradas + casos vectoriales.
- Mantiene reglas del modulo con criterio deterministico.
- Aplica reranking por afinidad para mejorar la relevancia de casos.

## 7. Proveedores LLM

El cliente remoto es compatible con endpoints estilo OpenAI Chat Completions.

Proveedores soportados:

- `ollama`
- `huggingface`
- `openai`

Comportamiento:

- si el proveedor elegido tiene `api_key`, `base_url` y `model`, se usa `RemoteLLMClient`
- si no, el sistema cae a `MockLLMClient`
- si el usuario pide explicitamente un proveedor mal configurado, la API responde `400`

## 8. Requisitos previos

| Herramienta | Version sugerida | Uso |
|---|---|---|
| Python | 3.11+ | runtime |
| uv | 0.5+ | entorno y dependencias |
| Ollama | opcional | pruebas locales con LLM |

Instalacion de `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

## 9. Instalacion

```bash
git clone <url-del-repositorio>
cd ia-generativa-rag
uv sync --extra dev
source .venv/bin/activate
```

Para validar instalacion:

```bash
python -m pytest tests -q
```

## 10. Configuracion con `.env`

El proyecto ahora usa un unico archivo `.env` para configuracion local.

Pasos recomendados:

1. copia `.env.example` a `.env`
2. completa las variables del proveedor que vayas a usar
3. define `RETRIEVER_MODE`
4. levanta la API

### Variables core

| Variable | Default | Descripcion |
|---|---|---|
| `LLM_API_KEY` | null | compatibilidad general para proveedor por defecto |
| `LLM_BASE_URL` | null | compatibilidad general para endpoint OpenAI-compatible |
| `LLM_MODEL` | null | compatibilidad general para modelo |
| `LLM_DEFAULT_PROVIDER` | `ollama` | proveedor inicial en la UI |
| `LLM_TIMEOUT_SECONDS` | `20` | timeout de llamadas LLM |
| `RETRIEVER_MODE` | `jaccard` | `jaccard`, `vector` o `hybrid` |

### Variables por proveedor

| Variable | Default | Descripcion |
|---|---|---|
| `OLLAMA_API_KEY` | `ollama` | API key local para Ollama |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434/v1` | endpoint compatible |
| `OLLAMA_MODEL` | `qwen2.5:7b` | modelo local |
| `HUGGINGFACE_API_KEY` | null | token de Hugging Face |
| `HUGGINGFACE_BASE_URL` | `https://router.huggingface.co/v1` | endpoint HF Router |
| `HUGGINGFACE_MODEL` | `meta-llama/Llama-3.1-8B-Instruct` | modelo remoto |
| `OPENAI_API_KEY` | null | API key OpenAI |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | endpoint OpenAI |
| `OPENAI_MODEL` | `gpt-4.1-mini` | modelo remoto |

### Variables vectoriales

| Variable | Default | Descripcion |
|---|---|---|
| `VECTOR_STORE_PATH` | `./data/chroma_db` | ruta del indice persistente |
| `VECTOR_COLLECTION_NAME` | `adm_knowledge_base` | nombre de la coleccion |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | modelo de embeddings |
| `KNOWLEDGE_DOCS_PATH` | null | carpeta opcional de PDFs |
| `VECTOR_REBUILD_INDEX` | `false` | fuerza rebuild al arranque |
| `VECTOR_REBUILD_POLICY` | `incremental` | `full` o `incremental` |

### Variables hybrid

| Variable | Default | Descripcion |
|---|---|---|
| `HYBRID_RETRIEVER_MODE` | `false` | habilita configuracion hybrid |
| `HYBRID_K_SIMILAR_CASES` | `5` | top-k de casos |
| `HYBRID_AFFINITY_THRESHOLD` | `0.0` | umbral minimo |
| `HYBRID_AFFINITY_BOOST_FACTOR` | `1.2` | boost por afinidad |
| `HYBRID_VECTOR_WEIGHT` | `0.7` | peso relativo del vectorial |
| `HYBRID_RULES_EXACT_MATCH_ONLY` | `true` | reglas estructuradas exactas |

## 11. Como correr la app

### Opcion A. Demo rapida sin LLM remoto

```bash
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

### Opcion B. Retrieval vectorial

Primer arranque con rebuild:

```bash
RETRIEVER_MODE=vector \
VECTOR_REBUILD_INDEX=true \
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

Arranques siguientes:

```bash
RETRIEVER_MODE=vector \
VECTOR_REBUILD_INDEX=false \
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

### Opcion C. Vector + Ollama

```bash
OLLAMA_API_KEY=ollama \
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 \
OLLAMA_MODEL=qwen2.5:7b \
LLM_DEFAULT_PROVIDER=ollama \
RETRIEVER_MODE=vector \
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

### Opcion D. Hybrid + Hugging Face

```bash
HUGGINGFACE_API_KEY=hf_xxx \
HUGGINGFACE_BASE_URL=https://router.huggingface.co/v1 \
HUGGINGFACE_MODEL=meta-llama/Llama-3.1-8B-Instruct \
LLM_DEFAULT_PROVIDER=huggingface \
RETRIEVER_MODE=hybrid \
HYBRID_RETRIEVER_MODE=true \
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

### Opcion E. Comparacion de 3 modelos en la UI

```bash
OLLAMA_API_KEY=ollama \
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 \
OLLAMA_MODEL=qwen2.5:7b \
HUGGINGFACE_API_KEY=hf_xxx \
HUGGINGFACE_BASE_URL=https://router.huggingface.co/v1 \
HUGGINGFACE_MODEL=meta-llama/Llama-3.1-8B-Instruct \
OPENAI_API_KEY=sk_xxx \
OPENAI_BASE_URL=https://api.openai.com/v1 \
OPENAI_MODEL=gpt-4.1-mini \
LLM_DEFAULT_PROVIDER=openai \
RETRIEVER_MODE=vector \
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

## 12. URLs utiles

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/metadata`
- `http://127.0.0.1:8000/enrichment/status`

## 13. Endpoints principales

| Endpoint | Metodo | Uso |
|---|---|---|
| `/` | GET | UI principal |
| `/health` | GET | healthcheck |
| `/metadata` | GET | catalogos, proveedores, indice y estado runtime |
| `/recomendar-rol` | POST | recomendacion principal |
| `/analizar-impacto-licencias` | POST | reporte mock de impacto externo |
| `/enrichment/status` | GET | estado de documentos y sinteticos |
| `/enrichment/document` | POST | agrega texto plano |
| `/enrichment/document-upload` | POST | sube `.txt`, `.md` o `.pdf` |
| `/enrichment/synthetic-cases` | POST | genera casos sinteticos |
| `/enrichment/reindex` | POST | reindexa el vector store |

## 14. Flujo exacto de la UI

### Carga inicial

1. la UI abre en `/`
2. llama `GET /metadata`
3. llena selectores de modulo y proveedor
4. muestra badges de LLM, modelo, conexion y retriever
5. muestra estado del indice y del enrichment

### Recomendacion

1. el usuario diligencia `cargo`, `modulo_asignado`, `descripcion_adicional`
2. la UI envia `POST /recomendar-rol`
3. muestra rol, permisos, confianza, justificacion y referencias recuperadas
4. despues dispara `POST /analizar-impacto-licencias`
5. renderiza clasificacion, riesgo, costos mock, areas aprobadoras y evidencias

## 15. Flujo interno del codigo

### `GET /metadata`

En [src/rag_adm/main.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/main.py:127):

- carga la base de conocimiento
- obtiene configuracion desde `settings.py`
- reporta proveedores soportados y modelo por proveedor
- informa estado del retriever y del indice vectorial
- informa cuantos documentos extra y sinteticos existen

### `POST /recomendar-rol`

En [src/rag_adm/main.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/main.py:179):

1. valida el request con `RecommendationRequest`
2. resuelve el proveedor LLM pedido
3. delega a `RolePermissionRecommender.recommend()`

Dentro de [src/rag_adm/recommender.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/recommender.py:17):

1. recupera reglas
2. recupera casos
3. recupera documentos de apoyo
4. crea un `PromptBundle`
5. obtiene roles y permisos validos
6. invoca `complete()` del cliente LLM activo
7. retorna `RecommendationResponse` con trazabilidad

### `POST /analizar-impacto-licencias`

En [src/rag_adm/main.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/main.py:189):

1. reutiliza el retriever para buscar documentos de apoyo relacionados con costos y licencias
2. llama `analyze_license_impact()`
3. construye `LicenseImpactResponse`

Dentro de [src/rag_adm/license_impact.py](/home/alejandro/dev/ia-generativa-rag/src/rag_adm/license_impact.py:18):

1. carga el catalogo mock
2. identifica reglas de impacto que aplican al modulo y permisos
3. consolida riesgos y clasificacion general
4. agrega evidencias del catalogo y del retriever vectorial

## 16. Ejemplos de uso

### Recomendacion

```bash
curl -X POST http://127.0.0.1:8000/recomendar-rol \
  -H "Content-Type: application/json" \
  -d '{
    "cargo": "Analista de soporte ADM",
    "modulo_asignado": "ADM",
    "descripcion_adicional": "Gestiona usuarios, revisa permisos y audita accesos.",
    "llm_provider": "openai"
  }'
```

### Impacto de licencias

```bash
curl -X POST http://127.0.0.1:8000/analizar-impacto-licencias \
  -H "Content-Type: application/json" \
  -d '{
    "cargo": "Analista de soporte ADM",
    "modulo_asignado": "ADM",
    "tipo_participante_inferido": "Administrador",
    "rol_recomendado": "Admin",
    "permisos_recomendados": ["gestionar_usuarios", "configurar_permisos", "auditar_accesos"]
  }'
```

## 17. Reindexacion manual

Sin levantar la API:

```bash
python scripts/reindex_vector_store.py --mode full
python scripts/reindex_vector_store.py --mode incremental
```

Con la API arriba:

```bash
curl -X POST http://127.0.0.1:8000/enrichment/reindex
```

## 18. Estructura del proyecto

```text
ia-generativa-rag/
├── data/
│   ├── catalogo_permisos.json
│   ├── politicas_acceso.json
│   ├── historico_configuraciones.json
│   ├── historico_sintetico.json
│   ├── politicas_licencias_costos.json
│   ├── escenarios_impacto_licencias.json
│   └── user_knowledge/
├── docs/
├── scripts/
├── src/rag_adm/
│   ├── enrichment.py
│   ├── knowledge_base.py
│   ├── license_impact.py
│   ├── llm_client.py
│   ├── llm_parser.py
│   ├── main.py
│   ├── models.py
│   ├── prompt_builder.py
│   ├── recommender.py
│   ├── retriever.py
│   ├── settings.py
│   ├── vector_store.py
│   └── static/index.html
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

## 19. Testing

Pruebas relevantes:

- `tests/test_api.py`: contratos principales de la API.
- `tests/test_recommender.py`: flujo central de recomendacion.
- `tests/test_vector_retriever.py`: retrieval vectorial.
- `tests/test_hybrid_retriever.py`: reranking hibrido.
- `tests/test_license_impact.py`: clasificacion y evidencia del analisis de licencias.
- `tests/test_enrichment_api.py`: subida y reindexacion de documentos.

Ejecucion:

```bash
python -m pytest tests -q
```

## 20. Checklist de demo

1. verificar que `.env` tenga el proveedor correcto
2. levantar la API
3. abrir `/metadata` y revisar `llm_provider_default`, `llm_providers_disponibles` y `retriever_mode`
4. correr al menos una recomendacion por modulo
5. mostrar las referencias de reglas, casos y documentos
6. mostrar el bloque de impacto de licencias
7. si usas modo `vector` o `hybrid`, comprobar que el indice este valido

## 21. Notas importantes

- El input ya no exige `tipo_participante`; el sistema lo infiere desde el contexto recuperado.
- El fallback mock no solo redacta: toma una decision deterministica si el LLM remoto falla.
- El analisis de licencias es mock y sirve para simulacion academica, no para gobierno real de contratos.
- El modo `vector` depende de Chroma y embeddings. Si faltan dependencias, ese modo no levantara correctamente.
