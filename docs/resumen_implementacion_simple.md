# Resumen Simple de la Implementacion

Este documento explica en lenguaje sencillo que se ha hecho en el proyecto, por que se hizo y que sigue.

## 1. Que problema estamos resolviendo

En el modulo ADM de Evergreen, cuando se crea un usuario nuevo, un administrador debe decidir que rol y que permisos darle.

Ese proceso puede salir mal si:
- se asignan permisos de mas,
- se asignan permisos de menos,
- dos usuarios parecidos terminan con configuraciones diferentes.

Por eso propusimos un asistente RAG que ayude a recomendar:
- el rol adecuado,
- los permisos adecuados,
- una justificacion de por que esa recomendacion tiene sentido.

## 2. Que se hizo hasta ahora

Se hizo un prototipo inicial para que la idea no quede solo en el informe.

El prototipo ya puede:
- recibir los datos de un usuario nuevo,
- revisar reglas base del dominio ADM,
- revisar casos historicos parecidos,
- recomendar un rol,
- recomendar permisos,
- devolver una justificacion en espanol.

## 3. Como esta organizado

El proyecto quedo dividido en partes pequenas para que sea mas facil de entender y mejorar:

| Parte | Que hace |
|---|---|
| `src/rag_adm/main.py` | Expone la API del proyecto |
| `src/rag_adm/models.py` | Define las entradas y salidas del sistema |
| `src/rag_adm/knowledge_base.py` | Carga la informacion base del dominio |
| `src/rag_adm/recommender.py` | Decide el rol, los permisos y la confianza |
| `src/rag_adm/llm_client.py` | Genera la justificacion usando modo local o remoto |
| `src/rag_adm/prompt_builder.py` | Construye el prompt que se le enviaria al LLM |
| `data/` | Guarda politicas, permisos e historico |
| `tests/` | Verifica que el comportamiento esperado siga funcionando |

## 4. Que significa eso en palabras simples

Hoy el sistema hace este recorrido:

1. Un administrador envia los datos de un perfil.
2. El sistema busca reglas del modulo ADM relacionadas con ese perfil.
3. Tambien busca casos anteriores que se parezcan.
4. Con eso decide un rol probable.
5. Despues filtra los permisos validos para ese rol.
6. Finalmente genera una explicacion de la recomendacion.

## 5. Que ya esta funcionando

- Un endpoint `GET /health` para saber si la API esta viva.
- Un endpoint `GET /metadata` para ver informacion basica del conocimiento cargado.
- Un endpoint `POST /recomendar-rol` para pedir la recomendacion.
- Pruebas automaticas para escenarios base del dominio ADM.
- Un modo `mock` para funcionar sin conectarse a un proveedor externo.
- Un modo `remote` opcional si luego quieren conectarlo a un LLM compatible.

## 6. Que se corrigio durante la implementacion

Se encontro un error importante:

Antes, algunos perfiles tipo Invitado podian heredar permisos de administrador por culpa de casos historicos parecidos.

Eso ya se corrigio.

Ahora el sistema primero decide el rol y luego solo permite permisos que sean validos para ese rol.

## 7. Por que este paso era necesario

Este paso era importante porque el curso no solo busca una idea bonita en papel.

Tambien conviene demostrar que:
- la funcionalidad se puede traducir a una estructura real,
- las entradas y salidas del informe si sirven como contrato,
- la arquitectura propuesta si puede empezar a materializarse,
- el equipo tiene una base para una posible siguiente entrega o sustentacion tecnica.

En otras palabras: pasamos de una propuesta conceptual a un prototipo pequeno pero entendible.

## 8. Limitacion critica identificada

Despues de revisar el prototipo con detalle, se identifico una limitacion de diseno importante:

**El LLM no razona en el flujo actual. Solo redacta.**

El rol y los permisos los decide la logica deterministica (Counter + votos). El LLM solo recibe el resultado ya calculado y lo convierte en texto. Eso no es RAG real: es una plantilla con texto generado.

En un RAG bien disenado, el LLM debe:
- recibir el perfil del usuario,
- recibir el contexto recuperado (reglas y casos similares),
- razonar sobre ese contexto,
- decidir el rol, los permisos, la confianza y la justificacion.

## 9. Plan de implementacion — RAG real con Ollama

Se decidio evolucionar el prototipo para que el LLM tome las decisiones reales. Se usara Ollama como servidor LLM local.

### Requisitos de entorno

- Instalar Ollama: https://ollama.com/download
- Bajar el modelo recomendado:
  ```bash
  ollama pull qwen2.5:7b
  ```
- Arrancar el servidor (queda corriendo en background):
  ```bash
  ollama serve
  ```
- Configurar las variables de entorno del proyecto:
  ```bash
  export LLM_API_KEY=ollama
  export LLM_BASE_URL=http://localhost:11434/v1
  export LLM_MODEL=qwen2.5:7b
  export LLM_TIMEOUT_SECONDS=60
  ```

Ollama expone una API compatible con OpenAI en `/v1`, por lo que el `RemoteLLMClient` existente ya puede conectarse sin cambios en la capa HTTP.

### Por que qwen2.5:7b

Es el modelo open-source mas confiable para seguir instrucciones de formato JSON estructurado, que es exactamente lo que necesita el sistema para parsear la respuesta del LLM. Requiere ~4.4 GB de VRAM.

### Cambios necesarios en el codigo

#### Paso 1 — Redisenar el prompt (`prompt_builder.py`)

El prompt actual le dice al LLM: "justifica esta decision que ya tomamos".

El nuevo prompt debe decirle: "dado este perfil y este contexto, decide tu el rol, los permisos, la confianza y justifica". Ademas debe pedirle que responda en JSON con esta estructura exacta:

```json
{
  "rol_recomendado": "Admin" | "Invitado",
  "permisos_recomendados": ["permiso1", "permiso2"],
  "justificacion": "texto explicando el razonamiento",
  "nivel_confianza": "alto" | "medio" | "bajo"
}
```

#### Paso 2 — Agregar parser de respuesta LLM (`llm_parser.py`)

Nuevo modulo que:
- extrae el JSON de la respuesta del LLM (puede venir con texto adicional),
- valida que el rol exista en el catalogo,
- filtra permisos que no existan en el catalogo (prevencion de alucinaciones),
- lanza excepcion si la respuesta es invalida (para activar el fallback).

#### Paso 3 — Invertir el flujo en `recommender.py`

Flujo actual:
```
reglas + casos → votos → rol/permisos → LLM justifica
```

Flujo nuevo:
```
reglas + casos → prompt con contexto → LLM razona y decide → parser valida → respuesta
                                                                     ↓ si falla
                                                            fallback determinístico
```

La logica de votos (Counter) se conserva como fallback si el LLM no responde o responde con formato invalido.

#### Paso 4 — Actualizar tests

Los tests actuales asumen el flujo determinístico. Hay que agregar:
- tests con `MockLLMClient` que simule respuesta JSON valida,
- tests que verifiquen que la capa de validacion rechaza roles y permisos inexistentes,
- tests de integracion opcionales contra Ollama local (marcados para saltar si Ollama no esta disponible).

### Orden de implementacion recomendado

| Paso | Archivo a modificar | Descripcion |
|:---:|---|---|
| 1 | `src/rag_adm/prompt_builder.py` | Redisenar prompt para que el LLM decida en JSON |
| 2 | `src/rag_adm/llm_parser.py` | Nuevo: parser y validador de respuesta LLM |
| 3 | `src/rag_adm/llm_client.py` | Integrar parser en `RemoteLLMClient.complete()` |
| 4 | `src/rag_adm/recommender.py` | Invertir flujo: LLM decide, votos solo como fallback |
| 5 | `src/rag_adm/models.py` | Revisar si hay que ajustar algun contrato |
| 6 | `tests/` | Actualizar y ampliar tests |

## 10. Idea corta para explicarlo en clase

"Primero definimos la funcionalidad RAG en el informe. Construimos un prototipo inicial donde la logica deterministica tomaba las decisiones y el LLM solo justificaba. Luego identificamos que eso no era RAG real e invertimos el flujo: ahora el LLM recibe el contexto recuperado, razona y decide el rol y los permisos. La logica deterministica quedo como fallback de seguridad contra alucinaciones."
