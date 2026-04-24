# Codex Workspace Context - ia-generativa-rag

## Idioma y tono
- Responder en espanol.
- Mantener una redaccion tecnica, clara y util para informe universitario, demo y sustentacion oral.
- Conectar las explicaciones con Evergreen, especialmente el modulo ADM: usuarios, roles, permisos, login, agrocadenas, etapas y continuidad con el trabajo previo en Node-RED.

## Contexto del proyecto
- Proyecto del curso "Desarrollo de Software para Inteligencia Artificial Generativa".
- Caso de aplicacion: asistente RAG Evergreen multi-modulo para recomendar rol y permisos.
- Stack principal: FastAPI, Pydantic, httpx, LangChain, ChromaDB, FastEmbed, uv.
- Backend: `src/rag_adm/`.
- Frontend estatico: `src/rag_adm/static/index.html`.
- Datos base: `data/politicas_acceso.json`, `data/catalogo_permisos.json`, `data/historico_configuraciones.json`.
- Documentacion clave: `README.md`, `docs/plan_entrega2.md`, `docs/informe_tecnico_rag.md`.
- Agente de referencia: `.github/agents/ia-generativa-rag.agent.md`.

## Decision tecnica actual
- Para los siguientes pasos, operar principalmente con base de datos vectorial.
- Modo objetivo: `RETRIEVER_MODE=vector`.
- ChromaDB es el vector store local persistente.
- La recuperacion debe basarse en embeddings y documentos/casos indexados, no en Jaccard como camino principal.
- Jaccard puede quedar como fallback historico o comparativo, pero no debe guiar nuevas funcionalidades.
- Hybrid existe como modo experimental/comparativo; no priorizar nuevas dependencias sobre `HYBRID_*` salvo que se pida explicitamente.

## Objetivo de expansion RAG
- Fortalecer ingestion de conocimiento: documentos del usuario, reglas, historicos, PDFs/texto y casos sinteticos.
- Mejorar trazabilidad: mostrar fuentes recuperadas, scores, estado del indice y evidencia usada por el LLM.
- Mejorar calidad: evaluacion con dataset dorado, metricas de rol/permisos/confianza y reportes reproducibles.
- Mantener respuestas estructuradas: rol recomendado, permisos recomendados, justificacion, nivel de confianza, tipo participante inferido y referencias recuperadas.
- Cuidar anti-alucinacion: validar roles y permisos contra catalogos locales antes de responder.

## Comandos utiles
- Instalar dependencias: `uv sync --extra dev`
- Correr API vectorial reconstruyendo indice:
  `RETRIEVER_MODE=vector VECTOR_REBUILD_INDEX=true python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000`
- Correr API vectorial sin rebuild:
  `RETRIEVER_MODE=vector VECTOR_REBUILD_INDEX=false python -m uvicorn rag_adm.main:app --app-dir src --host 127.0.0.1 --port 8000`
- Probar: `python -m pytest tests -q`

## Notas operativas
- No modificar cambios locales existentes sin revisarlos primero.
- Hay trabajo local en `src/rag_adm/llm_client.py`, `src/rag_adm/prompt_builder.py`, `src/rag_adm/static/index.html` y `uv.lock`.
- Si se actualiza documentacion, alinear README/plan/informe con la decision de trabajar en modo vector.
- Si se actualiza el frontend, preservar que sea una herramienta usable de demo, no una landing page.
