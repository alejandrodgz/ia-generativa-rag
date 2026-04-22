# Desarrollo de Software para Inteligencia Artificial Generativa
## Caso de Aplicacion — Asistente RAG Evergreen Multi-modulo (ADM, DIS, PLA, FIN)

Version final para compartir con el equipo y usar en presentacion.

---

## Equipo

| Integrante | Rol |
|---|---|
| Daniel Alejandro Garcia Zuluaica | Desarrollador |
| Juan Esteban Quintero Herrera | Desarrollador |
| Simon Ortiz Ohoa | Desarrollador |

Institucion: Universidad — Medellin, 2025-2026

---

## 1) Que resuelve este proyecto

Esta API recomienda un rol y permisos para un usuario de Evergreen a partir de su perfil.

Entrada principal:
- cargo
- modulo_asignado (ADM, DIS, PLA, FIN)
- tipo_participante
- descripcion_adicional (opcional)

Salida principal:
- rol_recomendado (Admin o Invitado)
- permisos_recomendados
- justificacion
- nivel_confianza
- trazabilidad de recuperacion (reglas, casos, documentos de apoyo, modo de retrieval)

El sistema soporta 3 estrategias de recuperacion:
- jaccard: reglas y casos por similitud de texto simple
- vector: recuperacion semantica con ChromaDB + embeddings
- hybrid: reglas exactas + casos vectoriales con reranking por afinidad

---

## 2) Requisitos previos

| Herramienta | Version minima | Uso |
|---|---|---|
| Python | 3.11+ | Runtime |
| uv | 0.5+ | Entorno y dependencias |
| Ollama | opcional | LLM local en modo remote |

Instalar uv (si no lo tienes):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

---

## 3) Montar el proyecto (paso a paso)

### Paso 1. Clonar y entrar

```bash
git clone <url-del-repositorio>
cd ia-generativa-rag
```

### Paso 2. Instalar dependencias

```bash
uv sync --extra dev
```

### Paso 3. Activar entorno

```bash
source .venv/bin/activate
```

### Paso 4. Validar que todo esta bien

```bash
python -m pytest tests -q
```

Resultado esperado actual: todos los tests en verde.

---

## 4) Ponerlo a correr

### Opcion A. Demo rapida (mock + jaccard)

No depende de Ollama.

```bash
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

### Opcion B. Vector (usa Chroma)

Primer arranque reconstruyendo indice:

```bash
RETRIEVER_MODE=vector \
VECTOR_REBUILD_INDEX=true \
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

Siguientes arranques (sin rebuild completo):

```bash
RETRIEVER_MODE=vector \
VECTOR_REBUILD_INDEX=false \
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

### Opcion C. Hybrid + Ollama (recomendado para presentacion)

1. Levantar Ollama:

```bash
ollama pull qwen2.5:7b
```

2. Correr API:

```bash
LLM_API_KEY=ollama \
LLM_BASE_URL=http://127.0.0.1:11434/v1 \
LLM_MODEL=qwen2.5:7b \
RETRIEVER_MODE=hybrid \
HYBRID_RETRIEVER_MODE=true \
HYBRID_K_SIMILAR_CASES=5 \
HYBRID_AFFINITY_BOOST_FACTOR=1.2 \
VECTOR_REBUILD_INDEX=false \
python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000
```

---

## 5) URLs clave

Con la API arriba:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/metadata
- http://127.0.0.1:8000/enrichment/status

---

## 6) Flujo exacto de informacion (campo por campo)

### 6.1 Flujo de carga inicial del front

1. El front abre en `/`.
2. JS llama `GET /metadata`.
3. Con `modulos_disponibles`, llena los selects:
   - `modulo` (formulario de recomendacion)
   - `doc-modulo` (formulario de carga de documentos)
4. Con `tipos_participante_disponibles`, llena `participante`.
5. Muestra badges de `llm_mode`, `retriever_mode` y estado del indice.

### 6.2 Flujo de recomendacion principal (`POST /recomendar-rol`)

Campos que envia el front:
- `cargo`
- `modulo_asignado`
- `tipo_participante`
- `descripcion_adicional`

Validacion de entrada (Pydantic):
- `cargo`: 1..100
- `modulo_asignado`: 1..20
- `tipo_participante`: 1..100
- `descripcion_adicional`: opcional, max 500

Recuperacion de contexto (RAG):
1. `retrieve_rules(request)`
   - usa `modulo_asignado` y `tipo_participante`
   - obtiene reglas exactas o por modulo
2. `retrieve_similar_cases(request)`
   - usa `cargo + modulo_asignado + tipo_participante + descripcion_adicional`
   - obtiene historicos similares
3. `retrieve_supporting_documents(request)`
   - usa query contextual + filtro por `modulo_asignado`
   - fallback a documentos `GLOBAL` si aplica

Decision:
1. Se arma `PromptBundle` con perfil + reglas + casos + documentos.
2. LLM (remote) o Mock (fallback) produce:
   - `rol_recomendado`
   - `permisos_recomendados`
   - `justificacion`
   - `nivel_confianza`

Respuesta final (`RecommendationResponse`):
- `rol_recomendado`
- `permisos_recomendados`
- `justificacion`
- `nivel_confianza`
- `casos_similares_ref`
- `retrieval_mode`
- `reglas_recuperadas_ref`
- `casos_similares_score`
- `documentos_apoyo_ref`
- `reranking_info` (si modo hybrid)

### 6.3 Flujo de enrichment de documentos

#### A) Texto directo (`POST /enrichment/document`)
Campos:
- `modulo_asignado`
- `title`
- `content`

Proceso:
1. Guarda archivo en `data/user_knowledge/` con patron por modulo.
2. Reindexa vector store (`force_full`).
3. Limpia caches runtime.
4. Devuelve conteo actualizado + estado de indice.

#### B) Archivo (`POST /enrichment/document-upload`)
Campos multipart:
- `file`
- `modulo_asignado`
- `title` (opcional)

Proceso igual al anterior: guardar -> reindexar -> responder estado.

### 6.4 Flujo de casos sinteticos (`POST /enrichment/synthetic-cases`)

Campos:
- `cargo`
- `modulo_asignado`
- `tipo_participante`
- `descripcion_base`
- `count` (1..10)

Proceso:
1. Genera casos sinteticos consistentes con politicas.
2. Los agrega al historico sintetico.
3. Reindexa.
4. Devuelve ids generados y nuevo total.

---

## 7) Endpoints principales

| Endpoint | Metodo | Uso |
|---|---|---|
| `/` | GET | Frontend |
| `/health` | GET | Healthcheck |
| `/metadata` | GET | Catalogos, modos, estado indice |
| `/recomendar-rol` | POST | Recomendacion principal |
| `/enrichment/status` | GET | Conteo de enrichment |
| `/enrichment/document` | POST | Agregar texto y reindexar |
| `/enrichment/document-upload` | POST | Subir archivo y reindexar |
| `/enrichment/synthetic-cases` | POST | Generar sinteticos y reindexar |
| `/enrichment/reindex` | POST | Reindexacion manual |

---

## 8) Ejemplo de uso rapido (curl)

```bash
curl -X POST http://127.0.0.1:8000/recomendar-rol \
  -H "Content-Type: application/json" \
  -d '{
    "cargo": "Operador de ruta regional",
    "modulo_asignado": "DIS",
    "tipo_participante": "Transportista",
    "descripcion_adicional": "Ejecuta entregas y consulta estado de envios"
  }'
```

---

## 9) Variables de entorno

### Core

| Variable | Default | Descripcion |
|---|---|---|
| `LLM_API_KEY` | null | Credencial del proveedor (si remote) |
| `LLM_BASE_URL` | null | Base URL compatible OpenAI |
| `LLM_MODEL` | null | Modelo LLM |
| `LLM_TIMEOUT_SECONDS` | `20` | Timeout de llamada LLM |
| `RETRIEVER_MODE` | `jaccard` | `jaccard`, `vector`, `hybrid` |

Nota: el modo LLM se infiere automaticamente. Si hay `LLM_API_KEY`, `LLM_BASE_URL` y `LLM_MODEL`, queda `remote`; de lo contrario usa `mock`.

### Vector

| Variable | Default | Descripcion |
|---|---|---|
| `VECTOR_STORE_PATH` | `./data/chroma_db` | Ruta del indice |
| `VECTOR_COLLECTION_NAME` | `adm_knowledge_base` | Nombre de coleccion |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Modelo de embeddings |
| `KNOWLEDGE_DOCS_PATH` | null | Carpeta PDF opcional |
| `VECTOR_REBUILD_INDEX` | `false` | Forzar rebuild al arranque |
| `VECTOR_REBUILD_POLICY` | `incremental` | `full` o `incremental` |

### Hybrid

| Variable | Default | Descripcion |
|---|---|---|
| `HYBRID_RETRIEVER_MODE` | `false` | Habilita config de hybrid |
| `HYBRID_K_SIMILAR_CASES` | `5` | Top-k de casos |
| `HYBRID_AFFINITY_THRESHOLD` | `0.0` | Umbral minimo |
| `HYBRID_AFFINITY_BOOST_FACTOR` | `1.2` | Boost por afinidad |
| `HYBRID_VECTOR_WEIGHT` | `0.7` | Peso vectorial |
| `HYBRID_RULES_EXACT_MATCH_ONLY` | `true` | Reglas exactas |

---

## 10) Reindexacion sin levantar API

```bash
python scripts/reindex_vector_store.py --mode full
python scripts/reindex_vector_store.py --mode incremental
```

---

## 11) Estructura del proyecto (resumen)

```text
ia-generativa-rag/
├── data/
│   ├── catalogo_permisos.json
│   ├── politicas_acceso.json
│   ├── historico_configuraciones.json
│   ├── historico_sintetico.json
│   ├── user_knowledge/
│   └── chroma_db/
├── docs/
├── src/rag_adm/
│   ├── main.py
│   ├── models.py
│   ├── knowledge_base.py
│   ├── retriever.py
│   ├── recommender.py
│   ├── prompt_builder.py
│   ├── llm_client.py
│   ├── llm_parser.py
│   ├── settings.py
│   └── static/index.html
├── tests/
├── pyproject.toml
└── README.md
```

---

## 12) Version para presentacion (guion corto, 7-10 min)

### Slide 1 - Problema
- En Evergreen hay altas y cambios de usuarios por modulo.
- Asignar permisos manualmente es lento y propenso a errores.
- Solucion: asistente RAG que recomienda rol y permisos con trazabilidad.

### Slide 2 - Arquitectura
- Frontend simple en FastAPI static.
- API en FastAPI.
- Base de conocimiento: permisos, politicas, historicos.
- Retriever configurable: jaccard, vector, hybrid.
- LLM mock o remote (Ollama).

### Slide 3 - Demo en vivo
- Mostrar `GET /metadata` y modulos ADM/DIS/PLA/FIN.
- Ejecutar recomendacion para DIS y FIN.
- Mostrar `documentos_apoyo_ref`, `casos_similares_ref`, `retrieval_mode`.

### Slide 4 - Enrichment
- Subir documento por modulo.
- Generar casos sinteticos.
- Reindexar y volver a consultar.
- Comparar justificacion antes/despues.

### Slide 5 - Cierre
- Valor: estandariza decisiones de acceso y acelera onboarding.
- Trazabilidad: reglas, casos y documentos recuperados.
- Escalabilidad: mismo patron para nuevos modulos.

---

## 13) Checklist final antes de compartir

1. `python -m pytest tests -q`
2. Abrir `http://127.0.0.1:8000/metadata` y validar modulos
3. Probar una recomendacion por cada modulo
4. Verificar que `documentos_apoyo_ref` aparezca en vector/hybrid
5. Compartir este README con el comando de arranque elegido
