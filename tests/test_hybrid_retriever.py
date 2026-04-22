from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("langchain_chroma")

from rag_adm.knowledge_base import KnowledgeBase
from rag_adm.models import RecommendationRequest
from rag_adm.retriever import JaccardRetriever, VectorRetriever, HybridRetriever
from rag_adm.settings import Settings, HybridSettings


def _vector_settings(tmp_path: Path) -> Settings:
    return Settings(
        llm_api_key=None,
        llm_base_url=None,
        llm_model=None,
        llm_timeout_seconds=20.0,
        retriever_mode="vector",
        vector_store_path=str(tmp_path / "chroma_db"),
        vector_collection_name="adm_test_collection",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        knowledge_docs_path=None,
        vector_rebuild_index=True,
        vector_rebuild_policy="full",
    )


def _hybrid_settings() -> HybridSettings:
    return HybridSettings(
        enabled=True,
        k_similar_cases=5,
        affinity_threshold=0.0,
        affinity_boost_factor=1.2,
        vector_weight=0.7,
        rules_exact_match_only=True,
    )


def test_hybrid_retriever_exact_rules_match(tmp_path: Path) -> None:
    """Validar que HybridRetriever recupera reglas exactas por modulo + tipo_participante."""
    base_path = Path(__file__).resolve().parents[1]
    kb = KnowledgeBase.load(base_path)

    jaccard = JaccardRetriever(kb)
    vector = VectorRetriever(kb, _vector_settings(tmp_path), base_path)
    hybrid = HybridRetriever(jaccard, vector, _hybrid_settings())

    reglas = hybrid.retrieve_rules(
        RecommendationRequest(
            cargo="Coordinador de agrocadena",
            modulo_asignado="ADM",
            tipo_participante="Productor",
            descripcion_adicional="",
        )
    )

    assert reglas
    assert reglas[0]["rol_preferido"] == "Invitado"
    assert "ver_agrocadenas" in reglas[0]["permisos"]


def test_hybrid_retriever_reranking_by_affinity(tmp_path: Path) -> None:
    """Validar que HybridRetriever aplica reranking por afinidad de tipo_participante."""
    base_path = Path(__file__).resolve().parents[1]
    kb = KnowledgeBase.load(base_path)

    jaccard = JaccardRetriever(kb)
    vector = VectorRetriever(kb, _vector_settings(tmp_path), base_path)
    hybrid = HybridRetriever(jaccard, vector, _hybrid_settings())

    casos = hybrid.retrieve_similar_cases(
        RecommendationRequest(
            cargo="Coordinador de agrocadena",
            modulo_asignado="ADM",
            tipo_participante="Productor",
            descripcion_adicional="Consulta etapas y seguimiento",
        )
    )

    # Validar que tenemos casos
    assert casos
    # Validar que los campos requeridos estén presentes
    assert all("id" in caso for caso in casos)
    assert all("_score" in caso for caso in casos)
    # Validar que se aplicó reranking
    assert all("_affinity_applied" in caso for caso in casos)

    # Contar casos con afinidad aplicada
    affinity_applied_count = sum(1 for caso in casos if caso.get("_affinity_applied", False))
    # Si hay casos con tipo_participante = "Productor", el boost debe haber sido aplicado
    if affinity_applied_count > 0:
        # Los casos con afinidad deben tener mejor score que los sin afinidad
        affinity_cases_scores = [c["_score"] for c in casos if c.get("_affinity_applied")]
        non_affinity_cases_scores = [c["_score"] for c in casos if not c.get("_affinity_applied")]
        if non_affinity_cases_scores and affinity_cases_scores:
            assert max(affinity_cases_scores) >= min(non_affinity_cases_scores)


def test_hybrid_retriever_respects_k_limit(tmp_path: Path) -> None:
    """Validar que HybridRetriever respeta el límite k_similar_cases."""
    base_path = Path(__file__).resolve().parents[1]
    kb = KnowledgeBase.load(base_path)

    jaccard = JaccardRetriever(kb)
    vector = VectorRetriever(kb, _vector_settings(tmp_path), base_path)

    # Configurar con k=2
    hybrid_settings = HybridSettings(
        enabled=True,
        k_similar_cases=2,
        affinity_threshold=0.0,
        affinity_boost_factor=1.2,
        vector_weight=0.7,
        rules_exact_match_only=True,
    )
    hybrid = HybridRetriever(jaccard, vector, hybrid_settings)

    casos = hybrid.retrieve_similar_cases(
        RecommendationRequest(
            cargo="Coordinador de agrocadena",
            modulo_asignado="ADM",
            tipo_participante="Productor",
            descripcion_adicional="",
        )
    )

    assert len(casos) <= 2


def test_hybrid_retriever_applies_threshold(tmp_path: Path) -> None:
    """Validar que HybridRetriever filtra por affinity_threshold."""
    base_path = Path(__file__).resolve().parents[1]
    kb = KnowledgeBase.load(base_path)

    jaccard = JaccardRetriever(kb)
    vector = VectorRetriever(kb, _vector_settings(tmp_path), base_path)

    # Configurar con threshold restrictivo
    hybrid_settings = HybridSettings(
        enabled=True,
        k_similar_cases=10,
        affinity_threshold=0.9,  # Solo recuperar casos con score >= 0.9
        affinity_boost_factor=1.2,
        vector_weight=0.7,
        rules_exact_match_only=True,
    )
    hybrid = HybridRetriever(jaccard, vector, hybrid_settings)

    casos = hybrid.retrieve_similar_cases(
        RecommendationRequest(
            cargo="Coordinador de agrocadena",
            modulo_asignado="ADM",
            tipo_participante="Productor",
            descripcion_adicional="",
        )
    )

    # Todos los casos deben cumplir el threshold
    assert all(caso["_score"] >= 0.9 for caso in casos)
