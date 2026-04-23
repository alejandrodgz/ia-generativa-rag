from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


class LLMDecisionError(Exception):
    """Se lanza cuando la respuesta del LLM no puede convertirse en una decision valida."""


@dataclass(slots=True)
class LLMDecision:
    rol_recomendado: str
    permisos_recomendados: list[str]
    justificacion: str
    nivel_confianza: str
    tipo_participante_inferido: str | None = None


_CONFIANZA_VALIDA = {"alto", "medio", "bajo"}


def parse_llm_response(
    text: str,
    roles_validos: set[str],
    permisos_validos: set[str],
) -> LLMDecision:
    """Extrae y valida una LLMDecision del texto crudo devuelto por el LLM.

    - Extrae el bloque JSON aunque venga con texto adicional o markdown.
    - Valida que rol_recomendado exista en el catalogo.
    - Filtra permisos_recomendados que no existan en el catalogo (anti-alucinaciones).
    - Lanza LLMDecisionError si la respuesta es invalida para activar el fallback.
    """
    raw = _extract_json(text)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMDecisionError(f"JSON invalido en respuesta del LLM: {exc}") from exc

    rol = data.get("rol_recomendado", "")
    if rol not in roles_validos:
        raise LLMDecisionError(f"Rol '{rol}' no existe en el catalogo: {roles_validos}")

    permisos_raw = data.get("permisos_recomendados", [])
    if not isinstance(permisos_raw, list):
        raise LLMDecisionError("permisos_recomendados debe ser una lista")
    permisos = [p for p in permisos_raw if isinstance(p, str) and p in permisos_validos]

    justificacion = str(data.get("justificacion", "")).strip()
    if len(justificacion) < 10:
        raise LLMDecisionError("justificacion demasiado corta o ausente en la respuesta del LLM")

    confianza = data.get("nivel_confianza", "")
    if confianza not in _CONFIANZA_VALIDA:
        confianza = "bajo"

    tipo_inferido = data.get("tipo_participante_inferido") or None
    if isinstance(tipo_inferido, str):
        tipo_inferido = tipo_inferido.strip() or None

    return LLMDecision(
        rol_recomendado=rol,
        permisos_recomendados=permisos,
        justificacion=justificacion,
        nivel_confianza=confianza,
        tipo_participante_inferido=tipo_inferido,
    )


def _extract_json(text: str) -> str:
    """Extrae el primer bloque JSON del texto, ignorando prosa o markdown circundante."""
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    raise LLMDecisionError("No se encontro bloque JSON en la respuesta del LLM")
