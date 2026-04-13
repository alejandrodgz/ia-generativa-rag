# Desarrollo de Software para Inteligencia Artificial Generativa
## Caso de Aplicación — Módulo ADM · Evergreen

**Entrega 1 — Funcionalidad RAG**

---

## Equipo

| Integrante | Rol |
|---|---|
| Daniel Alejandro Garcia Zuluaica | Desarrollador |
| Juan Esteban Quintero Herrera | Desarrollador |
| Simon Ortiz Ohoa | Desarrollador |

**Institución:** Universidad — Medellín, 2025-2026

---

## Contexto del Proyecto

Este repositorio documenta la primera entrega del curso **"Desarrollo de Software para Inteligencia Artificial Generativa"**, continuación del módulo anterior donde se trabajó con **Node-RED** sobre el caso de estudio **Evergreen**, específicamente el módulo **ADM (Administración)**.

El módulo ADM gestiona:
- Gestión de usuarios y autenticación (login)
- Control de acceso mediante roles y permisos
- Validaciones de datos (correo, teléfono)
- Agrocadenas y etapas del proceso productivo

---

## Entrega 1 — Informe Técnico RAG

En esta entrega se define una **funcionalidad RAG (Retrieval-Augmented Generation)** aplicable al módulo ADM de Evergreen, justificando su utilidad y proponiendo una arquitectura de solución.

### Estructura del informe

| Sección | Descripción |
|---|---|
| 1. Funcionalidad RAG | Nombre y presentación de la funcionalidad |
| 1.1 Presentación | Justificación y descripción clara |
| 1.2 Esquema explicativo | Vista de negocio (no de componentes software) |
| 2. Elementos de Datos | Base de conocimiento, entradas y salidas |
| 3. Arquitectura | Propuesta de vista física (UML / C4) |
| 4. Conclusiones | Reflexiones del equipo |

📄 Ver informe: [docs/informe_tecnico_rag.md](docs/informe_tecnico_rag.md)

📄 Ver resumen simple de avance: [docs/resumen_implementacion_simple.md](docs/resumen_implementacion_simple.md)

---

## Repositorio anterior (módulo previo)

El trabajo del módulo anterior (Node-RED / Herramientas para la Industrialización del Software) se encuentra documentado separadamente en el repositorio Node-RED del equipo.

---

## Prototipo inicial implementado

Ya existe una implementación mínima alineada con el alcance del curso. No intenta resolver un RAG completo en producción, sino materializar la idea del informe en un prototipo ejecutable y explicable.

### Qué incluye

| Componente | Ubicación | Propósito |
|---|---|---|
| API FastAPI | `src/rag_adm/main.py` | Expone el endpoint `POST /recomendar-rol` |
| Modelos tipados | `src/rag_adm/models.py` | Define contratos de entrada y salida |
| Base de conocimiento | `data/` | Contiene políticas, permisos e histórico inicial |
| Motor de recomendación | `src/rag_adm/recommender.py` | Resuelve rol, permisos y justificación |
| Pruebas | `tests/test_recommender.py` | Valida dos escenarios base del dominio ADM |

### Estructura implementada

```text
src/rag_adm/
	main.py
	models.py
	knowledge_base.py
	recommender.py
data/
	catalogo_permisos.json
	politicas_acceso.json
	historico_configuraciones.json
tests/
	test_recommender.py
```

### Cómo ejecutar el proyecto

Si ya tienen `uv` instalado:

```bash
uv run uvicorn rag_adm.main:app --app-dir src --reload
```

La API queda disponible en:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/metadata`
- `http://127.0.0.1:8000/docs`

### Modos de ejecución del LLM

El prototipo puede funcionar de dos formas:

| Modo | Comportamiento |
|---|---|
| `mock` | Genera la justificación con un cliente local determinístico, sin depender de servicios externos |
| `remote` | Usa un endpoint compatible con OpenAI para generar la justificación a partir del prompt y hace fallback a `mock` si falla |

Por defecto, si no configuran variables de entorno, el proyecto arranca en modo `mock`.

Para activar el modo `remote`, definan estas variables antes de ejecutar la API:

```bash
export LLM_API_KEY="<token>"
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o-mini"
export LLM_TIMEOUT_SECONDS="20"
```

#### Modo recomendado — Ollama local (RAG real)

Para correr el LLM localmente con Ollama (recomendado para demo y sustentación):

```bash
# 1. Instalar Ollama: https://ollama.com/download
# 2. Bajar el modelo
ollama pull qwen2.5:7b

# 3. El servidor arranca automáticamente con el primer uso,
#    o se puede levantar explícitamente:
ollama serve

# 4. Configurar el proyecto para apuntar a Ollama
export LLM_API_KEY=ollama
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=qwen2.5:7b
export LLM_TIMEOUT_SECONDS=60
```

Ollama expone una API compatible con OpenAI, por lo que el cliente existente se conecta sin cambios adicionales.

### Cómo ejecutar pruebas

```bash
uv run --extra dev pytest
```

### Ejemplo de uso

```bash
curl -X POST http://127.0.0.1:8000/recomendar-rol \
	-H "Content-Type: application/json" \
	-d '{
		"cargo": "Coordinador de agrocadena",
		"modulo_asignado": "ADM",
		"tipo_participante": "Productor",
		"descripcion_adicional": "Hace seguimiento operativo de etapas"
	}'
```

### Alcance actual del prototipo

- Sí incluye contratos claros, recuperación básica sobre conocimiento inicial y respuesta estructurada.
- Sí permite demostrar la continuidad entre Node-RED y la propuesta RAG del módulo ADM.
- No incluye una base vectorial real (el retrieval es por similitud de tokens Jaccard).
- Sí permite conexión opcional a cualquier proveedor compatible con OpenAI, incluido Ollama local.
- No reemplaza el informe técnico: lo complementa con una base ejecutable.

### Proxima evolucion planificada

Se identificó que en el prototipo actual el LLM solo justifica una decisión ya tomada por lógica determinística. El siguiente paso es invertir ese flujo para que el LLM razone y decida a partir del contexto recuperado (RAG real). Ver el plan detallado en [docs/resumen_implementacion_simple.md](docs/resumen_implementacion_simple.md#9-plan-de-implementacion--rag-real-con-ollama).

### Endpoints actuales

| Endpoint | Método | Propósito |
|---|---|---|
| `/health` | `GET` | Verifica que la API esté activa |
| `/metadata` | `GET` | Resume el estado del conocimiento cargado y el modo del LLM |
| `/recomendar-rol` | `POST` | Genera la recomendación de rol y permisos para un perfil ADM |

