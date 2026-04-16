from __future__ import annotations

from dataclasses import dataclass

from .knowledge_base import KnowledgeBase
from .models import RecommendationRequest, RecommendationResponse


@dataclass(slots=True)
class PromptBundle:
    perfil: RecommendationRequest
    reglas_relevantes: list[dict]
    casos_similares: list[dict]


class RolePermissionRecommender:
    """Orquesta el flujo RAG.

    Flujo principal:
        retriever recupera contexto → LLM decide rol/permisos/confianza/justificacion → respuesta

    Fallback (si el LLM falla o devuelve JSON invalido):
        MockLLMClient toma la decision de forma deterministica usando las reglas del bundle.
    """

    def __init__(self, knowledge_base: KnowledgeBase, llm_client, retriever) -> None:
        self.knowledge_base = knowledge_base
        self.llm_client = llm_client
        self.retriever = retriever

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        reglas = self.retriever.retrieve_rules(request)
        casos = self.retriever.retrieve_similar_cases(request)
        bundle = PromptBundle(perfil=request, reglas_relevantes=reglas, casos_similares=casos)

        roles_validos = self.knowledge_base.roles_validos()
        permisos_validos = self.knowledge_base.permisos_validos()

        decision = self.llm_client.complete(bundle, roles_validos, permisos_validos)

        return RecommendationResponse(
            rol_recomendado=decision.rol_recomendado,
            permisos_recomendados=decision.permisos_recomendados,
            justificacion=decision.justificacion,
            nivel_confianza=decision.nivel_confianza,
            casos_similares_ref=[caso["id"] for caso in casos],
        )
