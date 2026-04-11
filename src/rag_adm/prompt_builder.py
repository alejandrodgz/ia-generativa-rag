from __future__ import annotations

from .models import PromptMessage, RecommendationRequest
from .recommender import PromptBundle


def build_messages(bundle: PromptBundle, rol: str, permisos: list[str], confianza: str) -> list[PromptMessage]:
    reglas_texto = "\n".join(
        f"- Modulo: {regla['modulo']}, participante: {regla['tipo_participante']}, rol sugerido: {regla['rol_preferido']}, permisos: {', '.join(regla['permisos'])}"
        for regla in bundle.reglas_relevantes
    ) or "- No se encontraron reglas exactas; usar politicas generales del modulo."

    casos_texto = "\n".join(
        f"- Caso {caso['id']}: cargo={caso['cargo']}, rol={caso['rol']}, permisos={', '.join(caso['permisos'])}, similitud={caso.get('_score', 0):.2f}"
        for caso in bundle.casos_similares
    ) or "- No se encontraron casos historicos relevantes."

    perfil = _format_profile(bundle.perfil)
    permisos_texto = ", ".join(permisos) if permisos else "sin permisos adicionales"

    system_prompt = (
        "Eres un asistente de Evergreen ADM especializado en justificar la asignacion de roles y permisos. "
        "Debes responder en espanol, con tono tecnico y claro, sin inventar permisos inexistentes y mencionando al menos una fuente del contexto proporcionado."
    )
    user_prompt = (
        "Genera una justificacion breve y precisa para la recomendacion de acceso.\n"
        f"Perfil del usuario:\n{perfil}\n\n"
        f"Rol recomendado: {rol}\n"
        f"Permisos recomendados: {permisos_texto}\n"
        f"Nivel de confianza: {confianza}\n\n"
        f"Reglas recuperadas:\n{reglas_texto}\n\n"
        f"Casos similares recuperados:\n{casos_texto}\n\n"
        "Redacta un unico parrafo que explique por que la recomendacion es coherente con el dominio ADM."
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
