# Arquitectura del sistema RAG — Evergreen Multi-módulo

Diagramas de flujo del sistema. Dos vistas:
1. **Flujo principal** — recomendar rol (`POST /recomendar-rol`)
2. **Flujo enrichment** — subir documento y reindexar (`POST /subir-documento` + `POST /reindexar`)

---

## Diagrama 1 — Flujo principal: Recomendar rol

```mermaid
flowchart TD
    subgraph FE["Frontend - index.html"]
        A([Usuario llena formulario])
        B[cargo / modulo / tipo_participante / descripcion]
        C["fetch POST /recomendar-rol"]
        A --> B --> C
    end

    subgraph KB["Carga de conocimiento - KnowledgeBase"]
        KB1[politicas_acceso.json]
        KB2[catalogo_permisos.json]
        KB3[historico_configuraciones.json]
        KB4[data/user_knowledge/*.txt]
        KB5[(KnowledgeBase)]
        KB1 --> KB5
        KB2 --> KB5
        KB3 --> KB5
        KB4 --> KB5
    end

    subgraph API["API - main.py"]
        direction TB
        D["POST /recomendar-rol"]
        E[get_recommender]
        H[VectorRetriever]
        D --> E --> H
    end

    subgraph RET["Recuperacion RAG - retriever.py"]
        O1[Reglas por modulo y tipo]
        O3[Casos similares - Vector]
        O4[Documentos de apoyo - Vector]
        R[reglas_relevantes]
        S[casos_similares]
        T[documentos_apoyo]
        CTX[Contexto RAG unificado]
        O1 --> R
        O3 --> S
        O4 --> T
        R --> CTX
        S --> CTX
        T --> CTX
    end

    subgraph VEC["Indice vectorial - vector_store.py"]
        U[ChromaDB collection]
        V[all-MiniLM-L6-v2 embeddings]
        W[84 docs indexados]
        VX[Busqueda semantica top-k]
        U --> V --> W
        U --> VX
    end

    subgraph LLM["Decision LLM - llm_client.py + prompt_builder.py"]
        X[PromptBundle]
        Y[build_system_prompt + build_user_prompt]
        Z{LLM configurado}
        LA[MockLLMClient deterministico]
        LB[RemoteLLMClient Ollama qwen2.5:7b]
        LC[LLMDecision: rol / permisos / confianza / justificacion]
        X --> Y --> Z
        Z -- MOCK --> LA --> LC
        Z -- REMOTE --> LB --> LC
    end

    subgraph RESP["Respuesta - Frontend"]
        RA[RecommendationResponse]
        RB[Rol dentro del sistema]
        RC[Permisos recomendados]
        RD[Confianza y Justificacion]
        RA --> RB
        RA --> RC
        RA --> RD
    end

    C --> D
    E --> KB5
    KB5 --> H
    H --> O3
    H --> O4
    H --> O1
    H --> U
    VX --> O3
    VX --> O4
    CTX --> X
    LC --> RA
    RA --> A
```

> **RAG en 3 líneas:**
> - **R (Retrieval)**: VectorRetriever consulta ChromaDB y recupera reglas, casos similares y documentos relevantes.
> - **A (Augmented)**: ese contexto se empaqueta con el perfil del usuario en un prompt enriquecido (PromptBundle).
> - **G (Generation)**: Ollama (o Mock) recibe ese prompt aumentado y genera la recomendación de rol y permisos.

---

## Diagrama 2 — Flujo enrichment: Subir documento y reindexar

```mermaid
flowchart TD
    subgraph UP["Subir documento — POST /subir-documento"]
        A([Usuario sube archivo .txt]) --> B[save_uploaded_document\nenrichment.py]
        B --> C[data/user_knowledge/\nTIMESTAMP-nombre.txt]
    end

    subgraph GEN["Generar casos sintéticos — POST /generar-casos-sinteticos"]
        D[DocumentIngestRequest\ntítulo · contenido · módulo · tipo] --> E[generate_synthetic_cases\nllm_client.py]
        E --> F[Lista de SyntheticCase\nrol · permisos · justificación]
        F --> G[append_synthetic_cases\nhistorico_configuraciones.json]
    end

    subgraph REINDEX["Reindexar — POST /reindexar"]
        H[rebuild_runtime_index\nmain.py] --> I[reset_runtime_caches\nlru_cache limpia]
        I --> J[KnowledgeBase.load\nrecarga todos los archivos]
        J --> K[build_or_load_vector_store\nvector_store.py]
        K --> L{rebuild_policy}
        L -- full --> M[Elimina colección\nrecrea desde cero]
        L -- incremental --> N[Agrega solo docs nuevos]
        M & N --> O[(ChromaDB actualizada)]
    end

    subgraph RESIL["Resiliencia — retriever.py"]
        P[_safe_similarity_search] --> Q{NotFoundError?}
        Q -- sí --> R[_reload_vector_store\nreconstruye handle]
        R --> S[Reintento automático]
        Q -- no --> T[Resultado normal]
    end

    C --> D
    G --> H
    O --> P
```

---

## Diagramas ejecutivos (version clara para presentacion)

Estos diagramas complementan los tecnicos. Estan hechos para explicar el proceso en lenguaje simple, mostrando tecnologia por etapa y una palabra clave de accion.

### Diagrama 3 - Proceso completo con tecnologias

```mermaid
flowchart LR
    U[Usuario Web\nAccion: Solicita] --> F[Interfaz\nTecnologia: HTML + JS\nAccion: Captura]
    F --> A[API\nTecnologia: FastAPI\nAccion: Orquesta]
    A --> K[Base de conocimiento\nTecnologia: JSON + TXT\nAccion: Contextualiza]
    A --> R[Motor de recuperacion\nTecnologia: Jaccard o Vector o Hybrid\nAccion: Busca]
    R --> V[Indice semantico\nTecnologia: ChromaDB + all-MiniLM\nAccion: Encuentra]
    K --> P[Construccion de prompt\nTecnologia: prompt_builder.py\nAccion: Estructura]
    R --> P
    P --> L[Motor de decision\nTecnologia: Ollama qwen2.5 o Mock\nAccion: Decide]
    L --> S[Respuesta final\nTecnologia: JSON API\nAccion: Entrega]
    S --> F
    F --> U
```

### Diagrama 4 - Flujo de enrichment (mejora continua)

```mermaid
flowchart LR
    D[Documento nuevo\nAccion: Aporta] --> U1[Carga manual\nTecnologia: Frontend + FastAPI\nAccion: Sube]
    U1 --> W[Repositorio de contexto\nTecnologia: data/user_knowledge\nAccion: Guarda]
    W --> G[Generacion de casos\nTecnologia: LLM + reglas\nAccion: Amplia]
    G --> H[Historico\nTecnologia: historico_configuraciones.json\nAccion: Acumula]
    H --> I[Reindexacion\nTecnologia: vector_store.py\nAccion: Reconstruye]
    I --> C[ChromaDB\nAccion: Actualiza]
    C --> X[Retrieval en produccion\nTecnologia: retriever.py\nAccion: Reutiliza]
```

### Diagrama 5 - Lectura rapida por etapa

```mermaid
flowchart TD
    E1[Entrada\nFrontend\nPalabra: Capturar]
    E2[Orquestacion\nFastAPI\nPalabra: Coordinar]
    E3[Contexto\nJSON + TXT\nPalabra: Entender]
    E4[Recuperacion\nJaccard / Vector / Hybrid\nPalabra: Encontrar]
    E5[Decision\nOllama o Mock\nPalabra: Recomendar]
    E6[Salida\nRespuesta UI\nPalabra: Mostrar]

    E1 --> E2 --> E3 --> E4 --> E5 --> E6
```

---

## Referencias rápidas

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Rutas FastAPI, wiring de dependencias, lru_cache |
| `recommender.py` | Orquesta el flujo RAG: retriever → prompt → LLM → respuesta |
| `retriever.py` | JaccardRetriever, VectorRetriever, HybridRetriever |
| `knowledge_base.py` | Carga y normaliza las tres fuentes de datos + user_knowledge |
| `prompt_builder.py` | Construye system prompt y user prompt dinámicamente por módulo |
| `llm_client.py` | MockLLMClient (determinístico) y RemoteLLMClient (Ollama) |
| `vector_store.py` | Construye/carga colección ChromaDB, gestiona embeddings |
| `enrichment.py` | Guarda documentos subidos, genera casos sintéticos, dispara reindex |
| `settings.py` | Variables de entorno: RETRIEVER_MODE, LLM_*, HYBRID_*, VECTOR_* |
| `models.py` | Schemas Pydantic: Request, Response, LLMDecision, SyntheticCase |
