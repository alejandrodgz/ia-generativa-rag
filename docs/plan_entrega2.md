# Plan de Implementación — Entrega 2
## Arquitectura y Desarrollo para IA Generativa · Módulo ADM · Evergreen

---

## Qué exige la entrega 2

### Por sección del informe

| Sección | Qué hay que producir | Quién lo hace |
|---|---|---|
| **1.1 Vista Física** | Diagrama de arquitectura refinado (incorporar feedback entrega 1) | Todo el equipo |
| **1.2 Especificación de Componentes** | Tabla formal de cada componente: nombre, tipo, descripción, versión, consideraciones | Todo el equipo |
| **2.1 Base de Conocimiento** | Especificación formal de cada elemento: estructura, tipos de campo, formato (JSON/PDF/etc.), condiciones | Todo el equipo |
| **2.2 Diseño de Entradas** | Especificación formal de cada campo de entrada: tipo, formato, condiciones, esquema si aplica | Todo el equipo |
| **2.3 Diseño de Salidas** | Especificación formal de cada campo de salida: tipo, formato, condiciones (como entrada potencial de otro sistema) | Todo el equipo |
| **2.4 Diseño del Prompt** | Explicar estructura del prompt: parte fija vs parte variable, estrategia de reemplazo de texto | Todo el equipo |
| **3.1 Comparación por LLM** | Capturas de pantalla de cada LLM: lo que se envía y la respuesta obtenida | **1 LLM por integrante** |
| **3.2 Valoración de LLMs** | Criterios de evaluación (veracidad, relevancia, precisión, etc.) + tabla comparativa con justificación | Todo el equipo |
| **4.1 Librerías y Frameworks** | Análisis de la experiencia usando las librerías (`httpx`, `fastapi`, `pydantic`, etc.) | Todo el equipo |
| **4.2 Herramientas** | Análisis de la experiencia usando las herramientas (`uv`, `ollama`, VS Code, etc.) | Todo el equipo |
| **4.3 Conclusiones** | Lista de conclusiones por frente + consideraciones personales de cada integrante | Cada integrante |

### Restricciones importantes
- **Prohibido**: GPTs, Asistentes HuggingFace, Gems de Gemini, LangFlow, Flowise o cualquier plataforma Low-Code
- **Interfaz de usuario**: opcional. Si la hacen, solo una para el equipo que permita parametrizar el LLM a invocar
- **Presentación**: 15 minutos en PowerPoint, estructura = numerales del informe

---

## Asignación de LLMs (uno por integrante)

| Integrante | LLM sugerido | Modo de acceso |
|---|---|---|
| Daniel Alejandro Garcia | Ollama local (`qwen2.5:7b`) | `http://localhost:11434/v1` |
| Juan Esteban Quintero | Gemini (`gemini-1.5-flash`) | API key gratuita en Google AI Studio |
| Simon Ortiz | Groq (`llama-3.1-8b-instant`) | API key gratuita en console.groq.com |

> Todos son compatibles con el `RemoteLLMClient` existente vía variables de entorno. Solo cambia `LLM_BASE_URL`, `LLM_MODEL` y `LLM_API_KEY`.

---

## Tareas de código (en orden)

> **Decisión de diseño:** No se implementa base de datos vectorial en esta entrega.
> El retrieval se mantiene con similitud Jaccard sobre JSON. Sin embargo, **todo el código
> se escribe detrás de una interfaz `Retriever`** para que en el paso 7 se pueda
> reemplazar por ChromaDB sin tocar el resto del sistema.

### Paso 1 — `prompt_builder.py` ← **HACER PRIMERO**
Rediseñar el prompt para que el LLM **decida** el rol, permisos y confianza (no solo justifique).

El prompt nuevo debe:
- Incluir las reglas recuperadas y los casos similares como contexto
- Pedir respuesta en JSON con estructura exacta:
  ```json
  {
    "rol_recomendado": "Admin" | "Invitado",
    "permisos_recomendados": ["permiso1", "permiso2"],
    "justificacion": "texto explicando el razonamiento",
    "nivel_confianza": "alto" | "medio" | "bajo"
  }
  ```
- Separar claramente parte fija (instrucciones) de parte variable (perfil + contexto)

### Paso 2 — `llm_parser.py` *(archivo nuevo)*
Parser y validador de la respuesta JSON del LLM:
- Extraer el bloque JSON aunque venga con texto adicional
- Validar que `rol_recomendado` exista en el catálogo
- Filtrar `permisos_recomendados` que no estén en el catálogo (anti-alucinaciones)
- Lanzar excepción si la respuesta es inválida → activa el fallback

### Paso 3 — `llm_client.py`
Integrar el parser dentro de `RemoteLLMClient.complete()`:
- Si el LLM responde con JSON válido → retornar resultado parseado
- Si falla → lanzar excepción para que `recommender.py` active el fallback

### Paso 4 — `recommender.py`
Invertir el flujo:
```
ANTES: reglas + casos → votos → rol/permisos → LLM justifica
AHORA: reglas + casos → prompt → LLM decide → parser valida → respuesta
                                                      ↓ si falla
                                             fallback determinístico (votos)
```

### Paso 5 — `models.py`
Revisar si algún contrato necesita ajuste (probablemente no).

### Paso 6 — `tests/`
- Actualizar tests existentes que asumen flujo determinístico
- Agregar tests con `MockLLMClient` que simule JSON válido
- Agregar tests que verifiquen rechazo de roles/permisos inválidos
- Opcional: tests de integración contra Ollama (marcados para saltar si no está disponible)

---

## Paso 7 (FUTURO) — Incorporar base de datos vectorial

Este paso está diseñado para ejecutarse después de la entrega 2, sin romper nada de lo anterior.

### Qué se necesita instalar
```bash
uv add chromadb sentence-transformers
```

### Qué cambia en el código

El código de los pasos 1-6 usará una interfaz abstracta `Retriever` con dos métodos:
```python
def retrieve_rules(request) -> list[dict]: ...
def retrieve_similar_cases(request) -> list[dict]: ...
```

Hoy la implementará `JaccardRetriever` (lo que ya existe).
En el paso 7 se agrega `VectorRetriever` que usa ChromaDB, sin modificar
`recommender.py`, `prompt_builder.py` ni ningún otro componente.

### Cómo se activa
Variable de entorno:
```bash
export RETRIEVER_MODE=vector   # usa ChromaDB
export RETRIEVER_MODE=jaccard  # usa Jaccard (default)
```

### Esfuerzo estimado
~3-4 horas. No hacerlo antes de tener el LLM funcionando correctamente.

---

## Variables de entorno por LLM

```bash
# Ollama local
export LLM_API_KEY=ollama
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=qwen2.5:7b
export LLM_TIMEOUT_SECONDS=60

# Gemini (via API compatible OpenAI)
export LLM_API_KEY=<tu_api_key>
export LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
export LLM_MODEL=gemini-1.5-flash
export LLM_TIMEOUT_SECONDS=30

# Groq
export LLM_API_KEY=<tu_api_key>
export LLM_BASE_URL=https://api.groq.com/openai/v1
export LLM_MODEL=llama-3.1-8b-instant
export LLM_TIMEOUT_SECONDS=30
```

---

## Checklist del informe

### Sección 1
- [ ] Diagrama de arquitectura actualizado (incorporar feedback entrega 1)
- [ ] Tabla de especificación de todos los componentes (nombre, tipo, descripción, versión, consideraciones, recomendaciones)

### Sección 2
- [ ] Tabla de base de conocimiento: estructura de campos, tipos, formato, condiciones
- [ ] Tabla de entradas: estructura, tipos, formato, condiciones
- [ ] Tabla de salidas: estructura, tipos, formato, condiciones
- [ ] Explicación del prompt: parte fija vs variable, diagrama si aplica

### Sección 3
- [ ] Capturas de Daniel con su LLM (input + output)
- [ ] Capturas de Juan con su LLM (input + output)
- [ ] Capturas de Simon con su LLM (input + output)
- [ ] Criterios de valoración definidos y descritos
- [ ] Tabla comparativa de los 3 LLMs con justificación por criterio

### Sección 4
- [ ] Análisis de librerías usadas (`fastapi`, `pydantic`, `httpx`, `uvicorn`)
- [ ] Análisis de herramientas usadas (`uv`, `ollama`, VS Code, etc.)
- [ ] Conclusiones del equipo
- [ ] Consideraciones personales de cada integrante

### Presentación
- [ ] PowerPoint de 15 minutos
- [ ] Estructura = numerales del informe
- [ ] Demo en vivo o capturas de cada LLM funcionando
