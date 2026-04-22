from __future__ import annotations

import json

from .models import PromptMessage, RecommendationRequest
from .recommender import PromptBundle


def build_messages(
    bundle: PromptBundle,
    roles_validos: set[str],
    permisos_validos: set[str],
) -> list[PromptMessage]:
    """Construye los mensajes para el LLM.

    Parte FIJA: instrucciones del sistema, formato JSON esperado, listas de valores validos.
    Parte VARIABLE: perfil del usuario, reglas recuperadas, casos similares.

    El LLM debe decidir rol, permisos, justificacion y confianza — no solo justificar
    una decision ya tomada.
    """
    reglas_texto = "\n".join(
        f"- Modulo: {r['modulo']}, participante: {r['tipo_participante']}, "
        f"rol preferido: {r['rol_preferido']}, permisos sugeridos: {', '.join(r['permisos'])}"
        for r in bundle.reglas_relevantes
    ) or "- No se encontraron reglas exactas para este perfil."

    casos_texto = "\n".join(
        f"- Caso {c['id']}: cargo={c['cargo']}, tipo={c['tipo_participante']}, "
        f"rol={c['rol']}, permisos={', '.join(c['permisos'])}, similitud={c.get('_score', 0):.2f}"
        for c in bundle.casos_similares
    ) or "- No se encontraron casos historicos relevantes."

    documentos_texto = "\n".join(
        f"- Documento {d.get('title', d.get('source_file', 'sin titulo'))}: "
        f"{d.get('content_preview', '')} (similitud={d.get('_score', 0):.2f})"
        for d in bundle.documentos_apoyo
    ) or "- No se encontraron documentos de apoyo adicionales."

    roles_lista = json.dumps(sorted(roles_validos), ensure_ascii=False)
    permisos_lista = json.dumps(sorted(permisos_validos), ensure_ascii=False)

    # --- PARTE FIJA ---
    system_prompt = (
        "Eres un asistente experto en los modulos de Evergreen (ADM, DIS, PLA y FIN), especializado en asignacion de roles y permisos. "
        "Tu tarea es razonar sobre el perfil de un usuario y el contexto recuperado, y DECIDIR el rol y permisos adecuados. "
        "Debes responder UNICAMENTE con un objeto JSON valido, sin texto adicional antes ni despues del JSON."
    )

    # --- PARTE VARIABLE (perfil + contexto recuperado) + instruccion de formato ---
    user_prompt = (
        f"Dado el siguiente perfil de usuario y el contexto recuperado del dominio {bundle.perfil.modulo_asignado}, "
        "decide el rol y los permisos a asignar.\n\n"
        f"## Perfil del usuario\n{_format_profile(bundle.perfil)}\n\n"
        f"## Reglas del dominio {bundle.perfil.modulo_asignado} recuperadas\n{reglas_texto}\n\n"
        f"## Casos historicos similares\n{casos_texto}\n\n"
        f"## Documentos de apoyo adicionales\n{documentos_texto}\n\n"
        f"## Roles validos en el sistema\n{roles_lista}\n\n"
        f"## Permisos validos en el sistema\n{permisos_lista}\n\n"
        "Responde SOLO con este JSON (sin markdown, sin texto extra):\n"
        "{\n"
        '  "rol_recomendado": "<uno de los roles validos>",\n'
        '  "permisos_recomendados": ["<permiso1>", "<permiso2>"],\n'
        '  "justificacion": "<explicacion de minimo 50 caracteres citando al menos una regla o caso recuperado>",\n'
        '  "nivel_confianza": "<alto | medio | bajo>"\n'
        "}"
    )

    return [
        PromptMessage(role="system", content=system_prompt),
        PromptMessage(role="user", content=user_prompt),
    ]


def _format_profile(profile: RecommendationRequest) -> str:
    lines = [
        f"- Cargo: {profile.cargo}",
        f"- Modulo asignado: {profile.modulo_asignado}",
        f"- Tipo de participante: {profile.tipo_participante}",
    ]
    if profile.descripcion_adicional:
        lines.append(f"- Descripcion adicional: {profile.descripcion_adicional}")
    return "\n".join(lines)
