# Fase 2: Retrieval Híbrido y Reranking — Mejorar Calidad

## Objetivo

Implementar **retrieval híbrido** que combine:
- **Filtrado exacto estructurado** de reglas de negocio (por módulo + tipo de participante)
- **Búsqueda vectorial semántica** de casos similares
- **Reranking** por afinidad de módulo y tipo de participante

Resultado: mayor consistencia y precisión en recomendaciones, especialmente en casos ambiguos del dominio ADM.

## Alcance Técnico

### 1. Retrieval Híbrido (HybridRetriever)

**Estrategia**:
- Mantener dos implementaciones de retriever en paralelo: `JaccardRetriever` y `VectorRetriever`
- Crear nueva clase `HybridRetriever` que combine ambas lógicas inteligentemente
- Estrategia de recuperación:
  1. **Reglas** → Buscar EXACTAMENTE por `(modulo, tipo_participante)` en data estructurada
  2. **Casos** → Búsqueda vectorial semántica en Chroma
  3. Combinar resultados respetando orden y confidencia

**Pseudocódigo**:
```python
def retrieve_rules(self, cargo, modulo, tipo_participante):
    # Filtro exacto: modulo AND tipo_participante
    # No usar similitud; es una operación exacta
    return rules_matching(modulo=modulo, tipo_participante=tipo_participante)

def retrieve_similar_cases(self, contexto, k):
    # Búsqueda vectorial con scoring
    vector_results = self.vector_retriever.retrieve_similar_cases(contexto, k=k)
    # Rerank: elevar score si tipo_participante coincide
    reranked = self.rerank_by_affinity(vector_results, tipo_participante)
    return reranked
```

### 2. Reranking por Afinidad

**Lógica**:
- Para cada caso recuperado vectorialmente, evaluar coincidencia con `tipo_participante` del contexto
- Multiplicar score por factor de afinidad:
  - `score *= 1.2` si el tipo_participante en el caso coincide
  - `score *= 1.0` si no coincide (neutral)
- Re-ordenar casos por score ajustado
- Mantener top-k con los casos de mayor puntuación final

**Beneficio**: Casos del mismo tipo de participante suben en ranking, mejorando relevancia contextual.

### 3. Parametrización por Ambiente

Nuevas variables de entorno en `settings.py`:

| Variable | Tipo | Default | Rango | Descripción |
|----------|------|---------|-------|-------------|
| `HYBRID_RETRIEVER_MODE` | bool | `false` | true/false | Habilitar retrieval híbrido (vs sólo vector) |
| `HYBRID_K_SIMILAR_CASES` | int | 5 | 1-20 | Número de casos similares a recuperar |
| `HYBRID_AFFINITY_THRESHOLD` | float | 0.0 | 0.0-1.0 | Score mínimo para caso tras reranking |
| `HYBRID_AFFINITY_BOOST_FACTOR` | float | 1.2 | 1.0-2.0 | Multiplicador para casos con afinidad |
| `HYBRID_VECTOR_WEIGHT` | float | 0.7 | 0.0-1.0 | Peso del score vectorial en combinación |
| `HYBRID_RULES_EXACT_MATCH_ONLY` | bool | `true` | true/false | Filtrado exacto de reglas (vs fuzzy) |

### 4. Cambios en Modelos

**`RecommendationResponse`** (en `models.py`):
- Añadir campo `reranking_info` (dict opcional):
  ```json
  {
    "reranking_info": {
      "retriever_type": "hybrid",
      "rules_source": "structured_filter",
      "cases_retrieval_mode": "vector",
      "affinity_boosts_applied": 2,
      "top_k_threshold": 5,
      "affinity_boost_factor": 1.2
    }
  }
  ```

Este campo permite que el frontend vea exactamente qué estrategia se usó en el reranking.

## Cambios de Código

### Archivos a Modificar

#### 1. **src/rag_adm/settings.py**
- Importar nuevas variables de entorno HYBRID_*
- Crear clase `HybridSettings` o extender la configuración existente
- Validaciones: asegurar que thresholds y factores sean razonables

#### 2. **src/rag_adm/retriever.py**
- Crear clase `HybridRetriever` implementando la misma interfaz que `JaccardRetriever` y `VectorRetriever`
- Métodos:
  - `__init__(self, jaccard: JaccardRetriever, vector: VectorRetriever, settings: HybridSettings)`
  - `retrieve_rules()`: delegate a Jaccard (filtro exacto) o buscar en data estructurada directamente
  - `retrieve_similar_cases()`: llamar a VectorRetriever, luego rerank_by_affinity()
  - `_rerank_by_affinity()` (privado): aplicar boost a casos que coincidan en tipo_participante
- Instanciación en `main.py`: crear HybridRetriever cuando `RETRIEVER_MODE=hybrid`

#### 3. **src/rag_adm/models.py**
- Extender `RecommendationResponse` con campo `reranking_info: Optional[Dict[str, Any]]`
- Mantener backward compatibility (campo optional)

#### 4. **src/rag_adm/recommender.py**
- En el flujo de `recommend()`, detectar si el retriever es `HybridRetriever`
- Propagar info de reranking a `RecommendationResponse.reranking_info`
- Mantener compatibilidad con Jaccard y Vector puro

#### 5. **src/rag_adm/main.py**
- Actualizar factory de retrievers para instanciar `HybridRetriever` cuando sea necesario
- Registrar en logs que se está usando modo híbrido

#### 6. **tests/test_vector_retriever.py**
- Crear tests para `HybridRetriever`:
  - `test_hybrid_retriever_exact_rules_match()`: validar filtrado exacto de reglas
  - `test_hybrid_retriever_reranking_by_affinity()`: validar que casos con afinidad suben en score
  - `test_hybrid_retriever_respects_k_limit()`: validar top-k
  - `test_hybrid_retriever_applies_threshold()`: validar que casos bajo threshold se filtran
  - `test_hybrid_retriever_response_includes_reranking_info()`: validar que se propague metadato

## Criterios de Aceptación

✅ Retrieval híbrido puede activarse via `RETRIEVER_MODE=hybrid`  
✅ Reglas se recuperan exactamente por (modulo, tipo_participante)  
✅ Casos se rankean por similitud vectorial + afinidad  
✅ Nuevas variables de entorno respetan defaults sensatos  
✅ RecommendationResponse incluye reranking_info cuando modo hybrid activo  
✅ Tests validam lógica de afinidad y reranking  
✅ Frontend puede mostrar reranking_info en debug panel  
✅ Backward compatible: Jaccard y Vector puro siguen funcionando  

## Arquitectura Conceptual

```
┌─ Contexto de consulta ─────────────────────┐
│  cargo, modulo, tipo_participante           │
└──────────────┬──────────────────────────────┘
               │
        ┌──────▼──────┐
        │HybridRetriever
        └──────┬──────┘
               │
       ┌───────┴────────┐
       │                │
   ┌───▼────┐      ┌────▼────┐
   │Reglas  │      │Casos    │
   │Exactas │      │Vectorial│
   └───┬────┘      └────┬────┘
       │                │
       │          ┌─────▼─────┐
       │          │Reranking  │
       │          │(Afinidad) │
       │          └─────┬─────┘
       │                │
       └────────┬───────┘
                │
        ┌───────▼────────┐
        │Recommendation  │
        │+ reranking_info│
        └────────────────┘
```

## Riesgos y Mitigación

| Riesgo | Probabilidad | Mitigación |
|--------|:------------:|-----------|
| Reranking puede invertir orden esperado | Media | Tests exhaustivos de ordenamiento; factor configurable |
| Threshold muy restrictivo reduce resultados | Media | Default 0.0 (permisivo); documentar en settings |
| Performance: reranking adicional en cada query | Baja | Reranking es O(n) con n ≤ k (típicamente 5-10); negligible |
| Regresión: casos que funcionaban en Vector puro falla | Media | Tests de no-regresión; validación antes de activar |

## Orden de Implementación

1. Extender `settings.py` con variables HYBRID_*
2. Crear `HybridRetriever` en `retriever.py`
3. Registrar instantiación en `main.py`
4. Extender `models.py` con reranking_info
5. Actualizar `recommender.py` para propagar reranking_info
6. Implementar tests en `test_vector_retriever.py`
7. Validar manualmente en frontend con test case
8. Actualizar `/docs/plan_entrega2.md` si es necesario

## Entregable Verificable

**Ejecución**:
```bash
RETRIEVER_MODE=hybrid HYBRID_K_SIMILAR_CASES=5 HYBRID_AFFINITY_BOOST_FACTOR=1.2 \
python -m uvicorn rag_adm.main:app --host 127.0.0.1 --port 8000
```

**Test case**:
- Consulta: Coordinador de agrocadena, ADM, Productor
- Esperado:
  - Reglas exactas para (ADM, Productor)
  - Casos similares rankados con boost si tipo_participante=Productor
  - reranking_info en respuesta mostrando affinity_boosts_applied
  - Frontend actualiza debug panel con reranking_info

**Validación**:
- Casos con tipo_participante=Productor aparecen primero
- Casos sin afinidad aparecen después (pero conservan similitud vectorial)
- Tests de regresión: Jaccard y Vector puro siguen funcionando igual
