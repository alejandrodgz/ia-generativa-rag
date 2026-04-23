# Script de presentación — Base de conocimiento del sistema RAG
**Duración estimada:** ~3 minutos 30 segundos  
**Evento:** Sustentación Entrega 1 — Funcionalidad RAG Módulo ADM Evergreen  
**Curso:** Desarrollo de Software para Inteligencia Artificial Generativa 2026

---

## Diapositiva 1 — Base de conocimiento del sistema RAG
**Tiempo estimado: ~70 segundos**

> "El primer diseño que tomamos fue definir qué sabe el sistema antes de que alguien le pregunte algo. Esa decisión es la más importante de toda la arquitectura.
>
> En términos de IA, el problema no es solo "respuesta genérica"; el problema es **falta de grounding**. Un LLM puro optimiza probabilidad de siguiente token, no cumplimiento de política interna. Si no lo anclamos a evidencia del dominio, aumenta el riesgo de alucinación normativa: proponer permisos plausibles en lenguaje, pero incorrectos para la operación real.
>
> Por eso estructuramos la base en tres archivos con responsabilidades distintas y complementarias.
>
> El primero, `politicas_acceso.json`, contiene **16 reglas de negocio** que cruzan módulo con tipo de participante. Aquí modelamos la capa **normativa**: restricciones de acceso, límites y compatibilidades. Es la parte prescriptiva del sistema.
>
> El segundo, `catalogo_permisos.json`, tiene los **32 permisos** del sistema. Esta es la capa **ontológica**: define el vocabulario controlado para evitar ambigüedad semántica entre cómo habla el usuario y cómo se representan permisos en backend.
>
> El tercero, `historico_configuraciones.json`, guarda **29 casos reales** de asignaciones pasadas. Esta es la capa **empírica**: precedentes observados que permiten razonar por analogía y mejorar consistencia inter-caso.
>
> Con estas tres capas, el sistema no solo "responde": **constriñe, normaliza y justifica**. Además, al estar versionado en `data/`, podemos auditar cambios de política, reproducir decisiones y trazar por qué una recomendación cambió entre versiones."

---

## Diapositiva 2 — Entradas, procesador central y salidas
**Tiempo estimado: ~75 segundos**

> "El sistema expone una interfaz simple: recibe cuatro campos de entrada y devuelve cinco valores estructurados.
>
> Las entradas son: el **cargo** organizacional del usuario nuevo, el **módulo de Evergreen** al que va a pertenecer, el **tipo de participante** dentro de la agrocadena — que puede ser Productor, Distribuidor, Supervisor, entre otros — y una **descripción adicional** opcional que da contexto libre sobre sus responsabilidades.
>
> Con eso, el procesador central ejecuta un pipeline RAG con recuperación especializada por fuente.
>
> Primero, **recupera reglas aplicables** mediante filtros estructurados de módulo y tipo de participante. Segundo, **recupera casos similares** con búsqueda semántica vectorial sobre embeddings para aproximar vecindad conceptual, no coincidencia lexical. Tercero, **recupera documentos de soporte** cargados por usuarios para incorporar conocimiento operativo reciente.
>
> Las tres recuperaciones se fusionan en el `Unified RAG Context`, que funciona como contexto de evidencia y frontera de decisión del modelo. En otras palabras, desacoplamos "conocimiento de dominio" de "capacidad generativa".
>
> Las salidas son: el **rol recomendado**, la **lista de permisos** asociados, la **justificación** en texto del razonamiento, el **nivel de confianza** numérico, y las **referencias a casos similares** para trazabilidad.
>
> Un punto técnico clave es la política de fallback: si el `nivel_confianza` cae bajo umbral, el sistema marca el caso para revisión manual obligatoria. Esto evita automatización ciega y convierte al asistente en un sistema de soporte a decisión, no en un decisor autónomo."

---

## Diapositiva 3 — Flujo de información interno del sistema RAG
**Tiempo estimado: ~65 segundos**

> "Este diagrama muestra cómo fluye la información por dentro.
>
> Al arrancar la aplicación, los tres JSON más `user_knowledge` se transforman en chunks y se indexan en **ChromaDB**. Usamos `sentence-transformers/all-MiniLM-L6-v2` para generar embeddings de 384 dimensiones, optimizando costo/latencia sin perder semántica útil para el dominio.
>
> Cuando llega una solicitud, el **VectorRetriever** ejecuta recuperación top-k por tipo de fuente con filtros por `source_type` y `modulo`. Esa etapa combina recuperación densa y metadatos estructurados para evitar traer contexto irrelevante.
>
> El **Prompt Builder** serializa ese contexto en un prompt con contrato de salida. El LLM no responde libremente: responde bajo esquema, con campos explícitos y justificación verificable contra las evidencias recuperadas.
>
> Implementamos dos rutas de inferencia por configuración: **Mock determinístico** para pruebas reproducibles y **cliente remoto** para ejecución real, compatible con Ollama local (`qwen2.5:7b`) y Hugging Face (`Qwen/Qwen2.5-7B-Instruct`). La capa de negocio permanece estable; solo cambia el adaptador de inferencia.
>
> Por último, el enriquecimiento en vivo dispara reindexado automático ante nuevas fuentes. Eso nos da aprendizaje operativo incremental: la siguiente recomendación ya incorpora el nuevo contexto sin reentrenar el modelo base."

---

## Cierre (opcional, si hay tiempo)
**Tiempo estimado: ~20 segundos**

> "En resumen: la contribución técnica no es "usar un LLM", sino **diseñar una arquitectura RAG gobernable**. La base de conocimiento aporta restricciones, semántica y evidencia histórica; el LLM aporta síntesis y explicación. Esa separación de responsabilidades es lo que vuelve el sistema robusto, auditable y útil en producción."

---

## Notas de presentación

| Diapositiva | Énfasis clave | Pausa sugerida |
|---|---|---|
| 1 — Base de conocimiento | "grounding y control de alucinación normativa" — gancho técnico | Antes de presentar las 3 capas: normativa, ontológica, empírica |
| 2 — Entradas / Salidas | `nivel_confianza` bajo → revisión manual — muestra madurez de diseño | Antes de las salidas; dar tiempo para leer la lista |
| 3 — Flujo interno | Señalar físicamente los bloques del diagrama: KB → Index → RAG Context → LLM → Response | Antes de "dos modos de LLM" — cambio de tema |

### Números clave para recordar
- **16 reglas** de negocio en `politicas_acceso.json` (4 módulos × tipos de participante)
- **32 permisos** en `catalogo_permisos.json`
- **29 casos** en `historico_configuraciones.json`
- **16 tipos de participante** distintos
- **7 documentos** en `user_knowledge/` para contexto ampliado
- **21 tests** pasando — incluye integración y recomendaciones reales
- **384 dimensiones** por vector de embedding (`all-MiniLM-L6-v2`)
