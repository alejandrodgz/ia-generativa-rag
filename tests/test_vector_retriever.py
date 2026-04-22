from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("langchain_chroma")

from rag_adm.knowledge_base import KnowledgeBase
from rag_adm.models import RecommendationRequest
from rag_adm.retriever import VectorRetriever
from rag_adm.settings import Settings


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
    )


def test_vector_retriever_recupera_regla_de_productor(tmp_path: Path) -> None:
    base_path = Path(__file__).resolve().parents[1]
    kb = KnowledgeBase.load(base_path)
    retriever = VectorRetriever(kb, _vector_settings(tmp_path), base_path)

    reglas = retriever.retrieve_rules(
        RecommendationRequest(
            cargo="Coordinador de agrocadena",
            modulo_asignado="ADM",
            tipo_participante="Productor",
            descripcion_adicional="Consulta etapas y seguimiento de cadenas",
        )
    )

    assert reglas
    assert reglas[0]["rol_preferido"] == "Invitado"
    assert "ver_agrocadenas" in reglas[0]["permisos"]


def test_vector_retriever_recupera_casos_similares(tmp_path: Path) -> None:
    base_path = Path(__file__).resolve().parents[1]
    kb = KnowledgeBase.load(base_path)
    retriever = VectorRetriever(kb, _vector_settings(tmp_path), base_path)

    casos = retriever.retrieve_similar_cases(
        RecommendationRequest(
            cargo="Coordinador de agrocadena",
            modulo_asignado="ADM",
            tipo_participante="Productor",
            descripcion_adicional="Consulta etapas y seguimiento de cadenas",
        )
    )

    assert casos
    assert all("id" in caso for caso in casos)
    assert all("_score" in caso for caso in casos)
