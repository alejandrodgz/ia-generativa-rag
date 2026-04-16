from __future__ import annotations

import unicodedata
from typing import Protocol

from .knowledge_base import KnowledgeBase
from .models import RecommendationRequest


class Retriever(Protocol):
    """Interfaz de recuperacion de contexto.

    Implementaciones actuales: JaccardRetriever (similitud de tokens).
    Implementacion futura:     VectorRetriever  (ChromaDB / pgvector).
    Para activar el retriever vectorial en el futuro, basta con crear una clase
    que implemente estos dos metodos y pasarla al RolePermissionRecommender.
    """

    def retrieve_rules(self, request: RecommendationRequest) -> list[dict]: ...

    def retrieve_similar_cases(self, request: RecommendationRequest) -> list[dict]: ...


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
