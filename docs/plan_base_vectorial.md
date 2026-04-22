# Plan de Integracion de Base Vectorial

## Objetivo

Incorporar una base de datos vectorial local persistente al prototipo RAG del modulo ADM de Evergreen, usando LangChain, Chroma y FastEmbed, sin romper el flujo actual de recomendacion de roles y permisos.

## Alcance

- Mantener el retriever actual basado en Jaccard como modo por defecto y como fallback tecnico.
- Agregar un `VectorRetriever` configurable mediante variable de entorno.
- Indexar como documentos la base de conocimiento actual en JSON:
  - `data/politicas_acceso.json`
  - `data/catalogo_permisos.json`
  - `data/historico_configuraciones.json`
- Permitir indexar PDFs externos como fuente complementaria de contexto.
- Persistir el indice localmente con Chroma para evitar reindexar manualmente en cada ejecucion.

## Enfoque Tecnico

### 1. Configuracion

Se agregan nuevas variables de entorno para controlar el retrieval vectorial:

- `RETRIEVER_MODE=jaccard|vector`
- `VECTOR_STORE_PATH`
- `VECTOR_COLLECTION_NAME`
- `EMBEDDING_MODEL`
- `KNOWLEDGE_DOCS_PATH`
- `VECTOR_REBUILD_INDEX=true|false`

### 2. Fuentes a indexar

La base vectorial no se alimenta solo de PDFs. La fuente principal sigue siendo el conocimiento estructurado del dominio ADM.

#### Reglas de acceso

Cada regla de `politicas_acceso.json` se serializa como un documento con metadatos por modulo, tipo de participante y rol preferido.

#### Catalogo de permisos

Cada permiso se serializa como un documento independiente con su nombre, modulo y descripcion.

#### Historico de configuraciones

Cada caso historico se serializa como un documento con cargo, modulo, tipo de participante, rol asignado y permisos aplicados.

#### PDFs complementarios

Los PDFs se cargan con `PyMuPDFLoader`, se fragmentan con `RecursiveCharacterTextSplitter` y se etiquetan con metadatos de archivo y pagina.

## Cambios de Codigo

### `pyproject.toml`

Agregar dependencias:

- `chromadb`
- `langchain`
- `langchain-community`
- `langchain-chroma`
- `langchain-text-splitters`
- `fastembed`
- `pymupdf`

### `src/rag_adm/settings.py`

Extender configuracion para soportar base vectorial y rutas de persistencia.

### `src/rag_adm/knowledge_base.py`

Agregar metodos para convertir la base de conocimiento actual en documentos indexables con metadatos consistentes.

### `src/rag_adm/retriever.py`

Agregar una implementacion `VectorRetriever` que use Chroma y respete la misma interfaz `Retriever` ya definida.

### `src/rag_adm/main.py`

Elegir el retriever segun `RETRIEVER_MODE` sin modificar el contrato externo de la API.

### `src/rag_adm/vector_store.py`

Crear un modulo nuevo para centralizar:

- construccion de documentos de LangChain
- inicializacion de embeddings
- inicializacion de Chroma
- carga opcional de PDFs
- reindexacion del conocimiento

### `tests/`

Mantener las pruebas actuales para `JaccardRetriever` y agregar pruebas nuevas para `VectorRetriever`.

## Verificacion

1. Instalar dependencias nuevas y validar que el entorno resuelva imports de Chroma y FastEmbed.
2. Ejecutar las pruebas actuales con `RETRIEVER_MODE=jaccard` para confirmar compatibilidad hacia atras.
3. Ejecutar pruebas nuevas con `RETRIEVER_MODE=vector` para validar recuperacion de reglas y casos similares.
4. Levantar la API y probar `POST /recomendar-rol` en ambos modos.
5. Verificar que el indice se persista localmente y no se reconstruya salvo que se solicite.

## Decisiones

- Se implementa exactamente el stack solicitado en clase: LangChain + Chroma + FastEmbed.
- La base vectorial se construye primero sobre los JSON del dominio ADM porque contienen las reglas y precedentes reales del sistema.
- Los PDFs son una fuente complementaria y no reemplazan el conocimiento estructurado.
- Jaccard se conserva para comparacion academica, contingencia y pruebas.