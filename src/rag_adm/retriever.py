from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Protocol

from .knowledge_base import KnowledgeBase
from .models import RecommendationRequest
from .settings import Settings
from .vector_store import build_or_load_vector_store


class Retriever(Protocol):
    """Interfaz de recuperacion de contexto.

    Implementaciones actuales: JaccardRetriever (similitud de tokens).
    Implementacion futura:     VectorRetriever  (ChromaDB / pgvector).
    Para activar el retriever vectorial en el futuro, basta con crear una clase
    que implemente estos dos metodos y pasarla al RolePermissionRecommender.
    """

    def retrieve_rules(self, request: RecommendationRequest) -> list[dict]: ...

    def retrieve_similar_cases(self, request: RecommendationRequest) -> list[dict]: ...

    def retrieve_supporting_documents(self, request: RecommendationRequest) -> list[dict]: ...


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _tokenize(text: str) -> set[str]:
    cleaned = _normalize(text).replace("-", " ").replace("_", " ")
    return {token for token in cleaned.split() if token}


class JaccardRetriever:
    """Recuperacion por similitud de tokens (Jaccard).

    Sustituible por VectorRetriever sin cambiar ninguna otra clase.
    Activacion futura via variable de entorno RETRIEVER_MODE=vector.
    """

    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self.knowledge_base = knowledge_base

    def retrieve_rules(self, request: RecommendationRequest) -> list[dict]:
        modulo = _normalize(request.modulo_asignado)
        participante = _normalize(request.tipo_participante)
        reglas = [
            r
            for r in self.knowledge_base.politicas["reglas"]
            if _normalize(r["modulo"]) == modulo and _normalize(r["tipo_participante"]) == participante
        ]
        if reglas:
            return reglas
        return [
            r
            for r in self.knowledge_base.politicas["reglas"]
            if _normalize(r["modulo"]) == modulo
        ]

    def retrieve_similar_cases(self, request: RecommendationRequest) -> list[dict]:
        target_tokens = _tokenize(
            f"{request.cargo} {request.modulo_asignado} {request.tipo_participante} {request.descripcion_adicional or ''}"
        )
        scores: list[tuple[float, dict]] = []
        for case in self.knowledge_base.historico:
            case_tokens = _tokenize(
                f"{case['cargo']} {case['modulo_asignado']} {case['tipo_participante']} {case.get('descripcion_adicional', '')}"
            )
            union = len(target_tokens | case_tokens) or 1
            score = len(target_tokens & case_tokens) / union
            if score > 0:
                scores.append((score, case))
        scores.sort(key=lambda item: item[0], reverse=True)
        return [case | {"_score": score} for score, case in scores[:3]]

    def retrieve_supporting_documents(self, request: RecommendationRequest) -> list[dict]:
        _ = request
        return []


class VectorRetriever:
    """Recuperacion semantica sobre Chroma con embeddings FastEmbed."""

    def __init__(self, knowledge_base: KnowledgeBase, settings: Settings, base_path: Path) -> None:
        self.knowledge_base = knowledge_base
        self.settings = settings
        self.base_path = base_path
        self.vector_store = build_or_load_vector_store(knowledge_base, settings, base_path)

    def _is_missing_collection_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "collection" in message and "does not exist" in message

    def _reload_vector_store(self) -> None:
        self.vector_store = build_or_load_vector_store(self.knowledge_base, self.settings, self.base_path)

    def _safe_similarity_search(self, query: str, *, k: int, filter: dict) -> list[object]:
        try:
            return self.vector_store.similarity_search(query, k=k, filter=filter)
        except Exception as exc:
            if not self._is_missing_collection_error(exc):
                raise
            self._reload_vector_store()
            return self.vector_store.similarity_search(query, k=k, filter=filter)

    def _safe_similarity_search_with_score(self, query: str, *, k: int, filter: dict) -> list[tuple[object, float]]:
        try:
            return self.vector_store.similarity_search_with_score(query, k=k, filter=filter)
        except Exception as exc:
            if not self._is_missing_collection_error(exc):
                raise
            self._reload_vector_store()
            return self.vector_store.similarity_search_with_score(query, k=k, filter=filter)

    def retrieve_rules(self, request: RecommendationRequest) -> list[dict]:
        query = (
            "Regla de acceso para el modulo "
            f"{request.modulo_asignado} y tipo de participante {request.tipo_participante}."
        )

        docs = self._safe_similarity_search(
            query,
            k=6,
            filter={
                "$and": [
                    {"source_type": {"$eq": "regla"}},
                    {"modulo": {"$eq": request.modulo_asignado}},
                ]
            },
        )
        rules = [_doc_payload(doc) for doc in docs if _doc_payload(doc)]

        exact = [
            rule
            for rule in rules
            if _normalize(rule.get("tipo_participante", "")) == _normalize(request.tipo_participante)
        ]
        if exact:
            return exact
        if rules:
            return rules

        fallback_docs = self._safe_similarity_search(
            query,
            k=3,
            filter={"source_type": {"$eq": "regla"}},
        )
        return [_doc_payload(doc) for doc in fallback_docs if _doc_payload(doc)]

    def retrieve_similar_cases(self, request: RecommendationRequest) -> list[dict]:
        query = (
            f"Cargo {request.cargo}. Modulo {request.modulo_asignado}. "
            f"Tipo {request.tipo_participante}. Descripcion {request.descripcion_adicional or ''}."
        )

        docs_and_scores = self._safe_similarity_search_with_score(
            query,
            k=4,
            filter={
                "$and": [
                    {"source_type": {"$eq": "historico"}},
                    {"modulo": {"$eq": request.modulo_asignado}},
                ]
            },
        )

        result: list[dict] = []
        for doc, distance in docs_and_scores:
            payload = _doc_payload(doc)
            if not payload:
                continue
            similarity = 1.0 / (1.0 + float(distance))
            result.append(payload | {"_score": similarity})
        return result[:3]

    def retrieve_supporting_documents(self, request: RecommendationRequest) -> list[dict]:
        query = (
            f"Contexto de apoyo para cargo {request.cargo}. Modulo {request.modulo_asignado}. "
            f"Tipo {request.tipo_participante}. Descripcion {request.descripcion_adicional or ''}."
        )
        docs_and_scores = self._safe_similarity_search_with_score(
            query,
            k=3,
            filter={
                "$and": [
                    {"source_type": {"$eq": "extra_doc"}},
                    {"modulo": {"$eq": request.modulo_asignado}},
                ]
            },
        )

        if not docs_and_scores:
            docs_and_scores = self._safe_similarity_search_with_score(
                query,
                k=3,
                filter={
                    "$and": [
                        {"source_type": {"$eq": "extra_doc"}},
                        {"modulo": {"$eq": "GLOBAL"}},
                    ]
                },
            )

        result: list[dict] = []
        for doc, distance in docs_and_scores:
            payload = _doc_payload(doc)
            if not payload:
                continue
            similarity = 1.0 / (1.0 + float(distance))
            result.append(payload | {"_score": similarity})
        return result[:3]


class HybridRetriever:
    """Retrieval hibrido: reglas exactas + casos vectoriales con reranking por afinidad.

    Estrategia:
    - Reglas: filtrado exacto por (modulo, tipo_participante) en datos estructurados
    - Casos: busqueda vectorial semantica, luego rerank por afinidad de tipo_participante

    Fase 2 implementation: mejora consistencia en dominios estructurados como ADM.
    """

    def __init__(
        self,
        jaccard: JaccardRetriever,
        vector: VectorRetriever,
        settings: object,  # HybridSettings from settings.py
    ) -> None:
        self.jaccard = jaccard
        self.vector = vector
        self.settings = settings  # type: HybridSettings

    def retrieve_rules(self, request: RecommendationRequest) -> list[dict]:
        """Filtrado exacto de reglas por modulo + tipo_participante.

        Si settings.rules_exact_match_only=true (default), usa JaccardRetriever.
        """
        return self.jaccard.retrieve_rules(request)

    def retrieve_similar_cases(self, request: RecommendationRequest) -> list[dict]:
        """Busqueda vectorial de casos + reranking por afinidad de tipo_participante.

        Flujo:
        1. Llamar a VectorRetriever para obtener top-k casos por similitud
        2. Rerank: multiplicar score por affinity_boost_factor si tipo_participante coincide
        3. Re-ordenar y filtrar por affinity_threshold
        4. Retornar top-k rerankeados
        """
        # Obtener casos de VectorRetriever
        cases = self.vector.retrieve_similar_cases(request)
        if not cases:
            return cases

        # Reranking por afinidad
        reranked = []
        target_tipo = _normalize(request.tipo_participante)

        for case in cases:
            original_score = float(case.get("_score", 0.0))
            case_tipo = _normalize(case.get("tipo_participante", ""))

            # Aplicar boost si hay afinidad
            if case_tipo == target_tipo:
                boosted_score = original_score * self.settings.affinity_boost_factor
            else:
                boosted_score = original_score

            # Filtrar por threshold
            if boosted_score >= self.settings.affinity_threshold:
                reranked.append(case | {"_score": boosted_score, "_affinity_applied": case_tipo == target_tipo})

        # Re-ordenar por score descendente
        reranked.sort(key=lambda c: c.get("_score", 0.0), reverse=True)

        # Limitar a k_similar_cases
        return reranked[: self.settings.k_similar_cases]

    def retrieve_supporting_documents(self, request: RecommendationRequest) -> list[dict]:
        return self.vector.retrieve_supporting_documents(request)


def _doc_payload(doc: object) -> dict | None:
    metadata = getattr(doc, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    raw_payload = metadata.get("payload_json")
    if not isinstance(raw_payload, str):
        return None
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
