# Implementacion de Mejoras RAG Vectorial

## Objetivo de esta implementacion

Fortalecer la funcionalidad actual para que sea demostrable en frontend, trazable en backend y medible con pruebas, manteniendo compatibilidad con el flujo actual.

## Alcance inicial (Fase 1)

1. Exponer diagnostico de retrieval en la API:
- modo de retrieval activo (`jaccard` o `vector`)
- estado del indice vectorial
- tamano de coleccion vectorial
- ruta de persistencia del indice
- modelo de embeddings configurado

2. Incluir en la respuesta de recomendacion metadatos de recuperacion:
- reglas efectivamente usadas
- casos similares con score
- fuente principal de contexto

3. Mostrar diagnostico y trazabilidad en frontend:
- badge de modo retrieval
- panel de evidencia con top-k recuperado

4. Mantener compatibilidad:
- no romper endpoints existentes
- conservar modo `jaccard` como fallback
- mantener pruebas actuales y agregar nuevas donde aplique

## Cambios tecnicos planificados

### Backend

- `src/rag_adm/models.py`
  - ampliar contratos de respuesta para incluir metadatos de retrieval

- `src/rag_adm/recommender.py`
  - propagar trazabilidad del retrieval hacia la respuesta

- `src/rag_adm/main.py`
  - ampliar `/metadata` con estado de retrieval y vector store

- `src/rag_adm/retriever.py`
  - agregar informacion de diagnostico para cada retriever

- `src/rag_adm/vector_store.py`
  - exponer utilidades de estado del indice (count, path, disponibilidad)

### Frontend

- `src/rag_adm/static/index.html`
  - renderizar diagnostico de retrieval y evidencia recuperada

### Pruebas

- `tests/test_api.py`
  - validar presencia de campos de diagnostico sin romper compatibilidad

- `tests/test_vector_retriever.py`
  - reforzar cobertura de metadatos y score

## Criterios de aceptacion de esta fase

1. El endpoint `/metadata` debe mostrar claramente si esta en `vector` o `jaccard`.
2. En modo vector, debe reportarse tamano de indice y ruta de persistencia.
3. La UI debe permitir evidenciar el retrieval usado durante la recomendacion.
4. La suite de pruebas debe seguir en verde.

## Riesgos y mitigacion

1. Diferencias de entorno para embeddings:
- mitigacion: mantener fallback semantico cuando FastEmbed no este disponible.

2. Compatibilidad de clientes existentes:
- mitigacion: agregar campos nuevos sin eliminar los actuales.

3. Latencia por diagnostico:
- mitigacion: reutilizar componentes cacheados y evitar reconstrucciones innecesarias.

## Orden de ejecucion

1. Extender modelos y metadata backend.
2. Propagar trazabilidad en recomendacion.
3. Exponer y mostrar diagnostico en frontend.
4. Ajustar y ejecutar pruebas.
