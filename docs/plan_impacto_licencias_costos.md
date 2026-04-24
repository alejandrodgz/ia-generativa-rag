# Plan de Implementacion - Analisis de Impacto de Licencias y Costos

## Objetivo

Agregar al asistente RAG una segunda capa de recomendacion: despues de sugerir rol y permisos, el sistema debe indicar si esos permisos pueden generar costos adicionales, consumo de licencias, necesidad de modulos contratados, integraciones externas o aprobaciones internas.

Esta mejora convierte el prototipo de asignacion de roles en un asistente de gobierno de acceso para Evergreen. El administrador no solo ve que permisos asignar, sino tambien que implicaciones operativas, economicas y contractuales podria tener esa decision.

## Alcance de la primera version

La primera version sera un mock robusto basado en datos creados por el equipo. No se conectara todavia a GitHub, Workday, SAP SuccessFactors ni sistemas contables reales. El analisis se basara en:

- permisos recomendados por el RAG;
- modulo asignado;
- tipo de participante inferido;
- catalogo mock de sistemas externos, licencias y reglas de impacto;
- documentos indexados en Chroma para retrieval vectorial.

## Datos creados

### `data/politicas_licencias_costos.json`

Catalogo principal para el analisis estructurado.

Contiene:

- sistemas externos mock;
- modelos de costo mock;
- permisos externos disponibles;
- reglas de impacto por permiso Evergreen;
- heuristicas para clasificar el resultado;
- areas aprobadoras y acciones sugeridas.

Sistemas incluidos:

- Evergreen Core;
- GitHub Enterprise;
- SAP SuccessFactors HCM;
- Workday HCM;
- Atlas Contable Externo;
- API de Mapas y Logistica;
- BI Corporativo;
- Motor Analitico de Planeacion;
- Servicio de Notificaciones Externas.

### `data/escenarios_impacto_licencias.json`

Casos de prueba manual y futura base para pruebas automatizadas.

Incluye escenarios como:

- administrador ADM con integracion HCM;
- auditor externo con GitHub y BI;
- contador FIN con escritura contable;
- coordinador logistico con consumo de API de rutas;
- analista PLA con simulaciones y publicacion BI;
- tecnico DevOps con administracion GitHub.

### `data/user_knowledge/*.txt`

Documentos narrativos para que el modo vector pueda recuperar politicas de impacto desde Chroma.

Archivos agregados:

- `20260424090000-GLOBAL-politicas-licencias-costos.txt`;
- `20260424090001-ADM-impacto-licencias-accesos.txt`;
- `20260424090002-FIN-impacto-licencias-contables.txt`;
- `20260424090003-DIS-PLA-impacto-consumo-externo.txt`.

## Contrato propuesto de backend

### Nuevo modelo: `LicenseImpactRequest`

```json
{
  "cargo": "Analista de soporte ADM",
  "modulo_asignado": "ADM",
  "tipo_participante_inferido": "Administrador",
  "rol_recomendado": "Admin",
  "permisos_recomendados": ["gestionar_usuarios", "configurar_permisos"]
}
```

### Nuevo modelo: `LicenseImpactResponse`

```json
{
  "clasificacion_general": "requiere_validacion_contractual",
  "riesgo_general": "alto",
  "requiere_licencia_adicional": true,
  "requiere_modulo_adicional": true,
  "costo_estimado_mock": "12-18 por empleado/mes si el conector HCM no esta cubierto",
  "areas_aprobadoras": ["RRHH / TI", "TI / Seguridad"],
  "acciones_sugeridas": ["validar_con_area_responsable", "verificar_cupo_licencia"],
  "impactos": [
    {
      "regla_id": "LIC-ADM-001",
      "sistema": "SAP SuccessFactors HCM",
      "permisos_relacionados": ["gestionar_usuarios", "configurar_permisos"],
      "riesgo": "alto",
      "impacto_licencia": "posible_modulo_rrhh_o_conector_hcm",
      "explicacion": "Gestionar usuarios puede requerir consultar identidad laboral en HCM externo."
    }
  ],
  "evidencias_recuperadas": [
    {
      "tipo": "politica_vectorial",
      "titulo": "Politicas mock de licencias para permisos ADM",
      "resumen": "gestionar_usuarios y configurar_permisos pueden requerir HCM externo..."
    }
  ]
}
```

### Endpoint propuesto

```text
POST /analizar-impacto-licencias
```

## Logica recomendada

1. Recibir los permisos recomendados por el RAG.
2. Cargar `politicas_licencias_costos.json`.
3. Buscar reglas donde:
   - `modulo` coincida con el modulo asignado o sea `GLOBAL`;
   - algun permiso recomendado este en `permisos_evergreen`.
4. Inferir automaticamente los permisos externos y sistemas relacionados desde `permisos_externos_relacionados`.
5. Calcular riesgo general:
   - alto si existe al menos una regla de riesgo alto;
   - medio si existe al menos una regla de riesgo medio;
   - bajo si no hay reglas o solo hay impactos internos sin costo.
6. Calcular clasificacion general:
   - `requiere_validacion_contractual` si alguna regla requiere modulo adicional o tiene riesgo alto;
   - `requiere_licencia` si alguna regla requiere licencia adicional;
   - `posible_costo` si hay consumo por API, compute o mensajeria;
   - `sin_costo_aparente` si no se detectan impactos externos.
7. Recuperar documentos de apoyo desde Chroma con una query como:

```text
impacto licencias costos permisos ADM gestionar_usuarios configurar_permisos GitHub HCM
```

8. Devolver impactos estructurados, licencias inferidas y evidencias recuperadas.

## Cambios de frontend

Agregar un panel debajo de la recomendacion:

```text
Impacto de licencias y costos

Clasificacion: requiere validacion contractual
Riesgo: alto
Licencia adicional: si
Modulo adicional: si

Sistemas afectados:
- SAP SuccessFactors HCM
- Workday HCM
- GitHub Enterprise

Acciones sugeridas:
- Validar con RRHH / TI
- Verificar cupo de licencia GitHub
- Revisar contrato antes de aprobar
```

El usuario no debe seleccionar manualmente que licencias evaluar. La interfaz debe mostrar las licencias inferidas despues de la recomendacion, porque el flujo esperado es: el LLM recomienda permisos Evergreen y el analizador determina automaticamente que sistemas externos, seats o modulos podrian verse afectados.

## Valor para el usuario

- Evita aprobar permisos que generan costos inesperados.
- Ayuda a detectar si falta una licencia o modulo contratado.
- Da trazabilidad para justificar aprobaciones ante TI, Finanzas o RRHH.
- Muestra que el RAG no solo recomienda permisos, sino que razona sobre impacto operativo.
- Refuerza la sustentacion academica al conectar RAG con gobierno, costos e integraciones reales.

## Criterios de aceptacion

- El backend puede analizar permisos recomendados usando datos mock.
- El resultado incluye riesgo, clasificacion, sistemas afectados, areas aprobadoras y acciones sugeridas.
- El modo vector recupera documentos de politicas de licencias desde `data/user_knowledge/`.
- La UI muestra el analisis en un panel claro y no bloquea la recomendacion principal.
- Si no hay impactos detectados, el sistema debe decir `sin costo aparente` y explicar que no reemplaza validacion contractual final.

## Orden de implementacion

1. Crear modelos Pydantic para request/response.
2. Crear modulo `license_impact.py` para cargar catalogo y evaluar reglas.
3. Agregar endpoint `POST /analizar-impacto-licencias`.
4. Enriquecer retrieval vectorial para incluir documentos de licencias.
5. Agregar panel en `index.html`.
6. Agregar pruebas con `data/escenarios_impacto_licencias.json`.
7. Actualizar README con flujo demo.

## Nota de alcance

Los costos incluidos son mock y solo sirven para demostrar la funcionalidad. En una implementacion real, el sistema deberia consultar contratos, seats disponibles, modulos activos, consumo historico e integraciones aprobadas por Evergreen.

## Estado implementado

Implementado en esta iteracion:

- Catalogo mock de politicas, sistemas externos, reglas de impacto y escenarios demo.
- Endpoint `POST /analizar-impacto-licencias`.
- Inferencia automatica de licencias externas a partir de los permisos recomendados por el RAG.
- Evidencia vectorial recuperada desde documentos en `data/user_knowledge/`.
- Panel de UI para mostrar clasificacion, riesgo, licencias inferidas, costos mock, areas aprobadoras, acciones sugeridas, impactos y evidencias.
- Pruebas automatizadas para escenarios, inferencia de licencias y evidencia vectorial.

Validacion ejecutada:

```bash
.venv/bin/python -m pytest tests/test_license_impact.py -q
```

Resultado:

```text
5 passed
```

Tambien se reconstruyo el indice vectorial en modo `full`, quedando `vector_collection_size=88` e `index_metadata_valid=true`.
