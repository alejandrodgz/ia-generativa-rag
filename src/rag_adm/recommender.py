from __future__ import annotations

from dataclasses import dataclass

from .knowledge_base import KnowledgeBase
from .models import RecommendationRequest, RecommendationResponse


@dataclass(slots=True)
class PromptBundle:
    perfil: RecommendationRequest
    reglas_relevantes: list[dict]
    casos_similares: list[dict]
    documentos_apoyo: list[dict]


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

    def recommend(self, request: RecommendationRequest, llm_client=None) -> RecommendationResponse:
        reglas = self.retriever.retrieve_rules(request)
        casos = self.retriever.retrieve_similar_cases(request)
        documentos_apoyo = self.retriever.retrieve_supporting_documents(request)
        bundle = PromptBundle(
            perfil=request,
            reglas_relevantes=reglas,
            casos_similares=casos,
            documentos_apoyo=documentos_apoyo,
        )

        roles_validos = self.knowledge_base.roles_validos()
        permisos_validos = self.knowledge_base.permisos_validos()

        active_llm_client = llm_client or self.llm_client
        decision = active_llm_client.complete(bundle, roles_validos, permisos_validos)

        # Detectar tipo de retriever
        retriever_class = self.retriever.__class__.__name__
        if retriever_class == "HybridRetriever":
            retrieval_mode = "hybrid"
        elif retriever_class == "VectorRetriever":
            retrieval_mode = "vector"
        else:
            retrieval_mode = "jaccard"

        reglas_ref = [f"{regla.get('modulo', '')}:{regla.get('tipo_participante', '')}" for regla in reglas]
        casos_score = [
            {
                "id": str(caso.get("id", "")),
                "score": float(caso.get("_score", 0.0)),
            }
            for caso in casos
        ]
        documentos_apoyo_ref = [
            str(documento.get("title") or documento.get("source_file") or documento.get("id", ""))
            for documento in documentos_apoyo
        ]

        # Construir reranking_info si es retrieval híbrido
        reranking_info = None
        if retrieval_mode == "hybrid":
            affinity_boosts_applied = sum(1 for caso in casos if caso.get("_affinity_applied", False))
            reranking_info = {
                "retriever_type": "hybrid",
                "rules_source": "structured_exact_match",
                "cases_retrieval_mode": "vector_with_reranking",
                "affinity_boosts_applied": affinity_boosts_applied,
                "top_k_threshold": len(casos),
                "affinity_boost_factor": self.retriever.settings.affinity_boost_factor,
            }

        return RecommendationResponse(
            rol_recomendado=decision.rol_recomendado,
            permisos_recomendados=decision.permisos_recomendados,
            justificacion=decision.justificacion,
            nivel_confianza=decision.nivel_confianza,
            tipo_participante_inferido=decision.tipo_participante_inferido,
            casos_similares_ref=[caso["id"] for caso in casos],
            retrieval_mode=retrieval_mode,
            reglas_recuperadas_ref=reglas_ref,
            casos_similares_score=casos_score,
            documentos_apoyo_ref=documentos_apoyo_ref,
            reranking_info=reranking_info,
        )
