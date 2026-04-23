# Script de presentación — Base de conocimiento del sistema RAG
**Duración estimada:** ~3 minutos 30 segundos  
**Evento:** Sustentación Entrega 1 — Funcionalidad RAG Módulo ADM Evergreen  
**Curso:** Desarrollo de Software para Inteligencia Artificial Generativa 2026

---

## Diapositiva 1 — Base de conocimiento del sistema RAG
**Tiempo estimado: ~70 segundos**

> "El primer diseño que tomamos fue definir qué sabe el sistema antes de que alguien le pregunte algo. Esa decisión es la más importante de toda la arquitectura.
>
> Sin una base de conocimiento propia, el LLM respondería de forma genérica — y en un sistema de gestión agrícola como Evergreen, una recomendación genérica no sirve: podría asignarle permisos de administrador a alguien que solo debería leer reportes, o peor, denegar acceso a alguien que lo necesita para operar.
>
> Por eso estructuramos la base en tres archivos con responsabilidades distintas y complementarias.
>
> El primero, `politicas_acceso.json`, contiene **16 reglas de negocio** que cruzan módulo con tipo de participante — cuatro módulos del sistema Evergreen: ADM, DIS, PLA y FIN — y **16 tipos de participante** distintos, desde Productor hasta Auditor Financiero. Estas reglas definen qué puede hacer cada perfil.
>
> El segundo, `catalogo_permisos.json`, tiene los **32 permisos** del sistema, cada uno con nombre técnico, módulo al que pertenece y descripción en lenguaje natural. Es el vocabulario controlado — garantiza que el sistema siempre use la misma terminología al recomendar.
>
> El tercero, `historico_configuraciones.json`, guarda **29 casos reales** de asignaciones pasadas. Son los precedentes — cuando el sistema recomienda algo, puede apoyarse en situaciones similares que ya ocurrieron y funcionaron.
>
> Todo está en la carpeta `data/` del repositorio, versionado junto al código. Eso significa que la base de conocimiento es auditable, reproducible y mejorable de forma controlada."

---

## Diapositiva 2 — Entradas, procesador central y salidas
**Tiempo estimado: ~75 segundos**

> "El sistema expone una interfaz simple: recibe cuatro campos de entrada y devuelve cinco valores estructurados.
>
> Las entradas son: el **cargo** organizacional del usuario nuevo, el **módulo de Evergreen** al que va a pertenecer, el **tipo de participante** dentro de la agrocadena — que puede ser Productor, Distribuidor, Supervisor, entre otros — y una **descripción adicional** opcional que da contexto libre sobre sus responsabilidades.
>
> Con eso, el procesador central ejecuta lo que llamamos el ciclo RAG en tres pasos simultáneos.
>
> Primero, **recupera las reglas aplicables**: filtra las 16 reglas por el módulo y tipo de participante específico del caso. Segundo, **busca casos similares**: hace una búsqueda semántica en los 29 históricos para encontrar los precedentes más cercanos usando vectores de embeddings — no busca por palabras exactas, busca por significado. Tercero, **recupera documentos de apoyo**: cualquier documento adicional que haya sido subido por el equipo para enriquecer el contexto.
>
> Los tres resultados se unen en un único `Unified RAG Context` — la hoja de evidencia que recibe el LLM. El modelo no decide en el vacío: decide con contexto específico del negocio Evergreen.
>
> Las salidas son: el **rol recomendado**, la **lista de permisos** asociados, la **justificación** en texto del razonamiento, el **nivel de confianza** numérico, y las **referencias a casos similares** para trazabilidad.
>
> Un punto de diseño importante: si el `nivel_confianza` es bajo, el sistema lo señala explícitamente y recomienda revisión manual obligatoria. Esa salvaguarda la definimos desde el inicio para que el sistema nunca imponga una decisión que no puede sostener."

---

## Diapositiva 3 — Flujo de información interno del sistema RAG
**Tiempo estimado: ~65 segundos**

> "Este diagrama muestra cómo fluye la información por dentro.
>
> Al arrancar la aplicación, los tres archivos JSON más los documentos de `user_knowledge` se indexan en **ChromaDB** — una base de datos vectorial local. El modelo `sentence-transformers/all-MiniLM-L6-v2` convierte cada fragmento de texto en un vector numérico de 384 dimensiones. Eso se hace una sola vez, al inicio, y el índice queda listo en memoria para responder consultas en milisegundos.
>
> Cuando llega una solicitud, el **VectorRetriever** hace tres búsquedas semánticas en paralelo dentro de ese índice — una por cada tipo de fuente — usando filtros por `source_type` y `modulo`. El resultado converge en el contexto unificado, que pasa al **Prompt Builder**.
>
> El Prompt Builder arma el prompt final: incluye las instrucciones del sistema, el contexto recuperado y la solicitud del usuario, todo estructurado para que el LLM responda en el formato JSON que espera el sistema.
>
> Implementamos dos modos de LLM intercambiables por variable de entorno: un **cliente Mock** determinístico para testing — que permite correr los 21 tests del proyecto sin necesidad de conexión — y un **cliente remoto** que soporta tanto Ollama local con `qwen2.5:7b` como Hugging Face con `Qwen/Qwen2.5-7B-Instruct`. La lógica de negocio no cambia entre modos.
>
> Por último, el sistema también permite enriquecimiento en vivo: cualquier documento nuevo subido desde la interfaz desencadena un reindexado automático, y la siguiente consulta ya incorpora esa información. Así la base de conocimiento crece con el uso."

---

## Cierre (opcional, si hay tiempo)
**Tiempo estimado: ~20 segundos**

> "En resumen: la base de conocimiento es lo que transforma un LLM genérico en una herramienta especializada para Evergreen. Sin los tres archivos, el sistema no tiene vocabulario, no tiene reglas y no tiene precedentes. Con ellos, cada recomendación es consistente, justificada y trazable."

---

## Notas de presentación

| Diapositiva | Énfasis clave | Pausa sugerida |
|---|---|---|
| 1 — Base de conocimiento | "sin esto, el LLM falla" — es el gancho de entrada | Antes de mencionar cada archivo numerado |
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
