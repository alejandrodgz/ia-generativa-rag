from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import unicodedata

from .knowledge_base import KnowledgeBase
from .models import RecommendationRequest, RecommendationResponse


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _tokenize(text: str) -> set[str]:
    cleaned = _normalize(text).replace("-", " ").replace("_", " ")
    return {token for token in cleaned.split() if token}


@dataclass(slots=True)
class PromptBundle:
    perfil: RecommendationRequest
    reglas_relevantes: list[dict]
    casos_similares: list[dict]


class RolePermissionRecommender:
    def __init__(self, knowledge_base: KnowledgeBase, llm_client) -> None:
        self.knowledge_base = knowledge_base
        self.llm_client = llm_client

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        reglas = self._retrieve_rules(request)
        casos = self._retrieve_similar_cases(request)
        rol = self._resolve_role(reglas, casos)
        permisos = self._resolve_permissions(request, rol, reglas, casos)
        confianza = self._resolve_confidence(reglas, casos)
        bundle = PromptBundle(perfil=request, reglas_relevantes=reglas, casos_similares=casos)
        justificacion = self.llm_client.complete(bundle, rol, permisos, confianza)
        refs = [caso["id"] for caso in casos]
        return RecommendationResponse(
            rol_recomendado=rol,
            permisos_recomendados=permisos,
            justificacion=justificacion,
            nivel_confianza=confianza,
            casos_similares_ref=refs,
        )

    def _retrieve_rules(self, request: RecommendationRequest) -> list[dict]:
        modulo = _normalize(request.modulo_asignado)
        participante = _normalize(request.tipo_participante)
        reglas = []
        for regla in self.knowledge_base.politicas["reglas"]:
            modulo_match = _normalize(regla["modulo"]) == modulo
            participante_match = _normalize(regla["tipo_participante"]) == participante
            if modulo_match and participante_match:
                reglas.append(regla)
        if reglas:
            return reglas
        return [
            regla
            for regla in self.knowledge_base.politicas["reglas"]
            if _normalize(regla["modulo"]) == modulo
        ]

    def _retrieve_similar_cases(self, request: RecommendationRequest) -> list[dict]:
        scores: list[tuple[float, dict]] = []
        target_tokens = _tokenize(
            f"{request.cargo} {request.modulo_asignado} {request.tipo_participante} {request.descripcion_adicional or ''}"
        )
        for case in self.knowledge_base.historico:
            case_tokens = _tokenize(
                f"{case['cargo']} {case['modulo_asignado']} {case['tipo_participante']} {case.get('descripcion_adicional', '')}"
            )
            intersection = len(target_tokens & case_tokens)
            union = len(target_tokens | case_tokens) or 1
            score = intersection / union
            if score > 0:
                scores.append((score, case))
        scores.sort(key=lambda item: item[0], reverse=True)
        return [case | {"_score": score} for score, case in scores[:3]]

    def _resolve_role(self, reglas: list[dict], casos: list[dict]) -> str:
        role_votes = Counter()
        for regla in reglas:
            role_votes[regla["rol_preferido"]] += 2
        for caso in casos:
            role_votes[caso["rol"]] += 1
        rol = role_votes.most_common(1)[0][0] if role_votes else "Invitado"
        if rol not in self.knowledge_base.roles_validos():
            return "Invitado"
        return rol

    def _resolve_permissions(
        self,
        request: RecommendationRequest,
        rol: str,
        reglas: list[dict],
        casos: list[dict],
    ) -> list[str]:
        permissions = Counter()
        allowed_permissions = self._allowed_permissions_for_role(rol, request.modulo_asignado)
        for regla in reglas:
            for permiso in regla["permisos"]:
                if permiso in allowed_permissions:
                    permissions[permiso] += 2
        for caso in casos:
            if caso["rol"] != rol:
                continue
            for permiso in caso["permisos"]:
                if permiso in allowed_permissions:
                    permissions[permiso] += 1

        if not permissions:
            for permiso in allowed_permissions:
                permissions[permiso] += 1

        valid_permissions = self.knowledge_base.permisos_validos()
        result = [permiso for permiso, _ in permissions.most_common() if permiso in valid_permissions]
        return result[:5]

    def _allowed_permissions_for_role(self, rol: str, modulo_asignado: str) -> set[str]:
        modulo = modulo_asignado.upper()
        for role in self.knowledge_base.politicas["roles"]:
            if role["nombre"] == rol:
                return set(role["permisos_por_modulo"].get(modulo, []))
        return set()

    def _resolve_confidence(self, reglas: list[dict], casos: list[dict]) -> str:
        best_case_score = casos[0].get("_score", 0.0) if casos else 0.0
        if reglas and best_case_score >= 0.4:
            return "alto"
        if reglas or best_case_score >= 0.2:
            return "medio"
        return "bajo"
