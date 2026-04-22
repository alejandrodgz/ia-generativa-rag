from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .knowledge_base import KnowledgeBase
from .llm_client import build_llm_client
from .models import HealthResponse, MetadataResponse, RecommendationRequest, RecommendationResponse
from .recommender import RolePermissionRecommender
from .retriever import JaccardRetriever, VectorRetriever
from .settings import get_settings
from .vector_store import get_vector_index_status


_STATIC = Path(__file__).parent / "static"

app = FastAPI(
    title="Asistente RAG ADM",
    version="0.1.0",
    description="Prototipo minimo para recomendar roles y permisos en Evergreen ADM.",
)

app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/", include_in_schema=False)
def ui() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@lru_cache
def get_recommender() -> RolePermissionRecommender:
    base_path = Path(__file__).resolve().parents[2]
    knowledge_base = KnowledgeBase.load(base_path)
    settings = get_settings()
    llm_client = build_llm_client(settings)
    if settings.retriever_mode == "vector":
        retriever = VectorRetriever(knowledge_base, settings, base_path)
    else:
        retriever = JaccardRetriever(knowledge_base)
    return RolePermissionRecommender(knowledge_base, llm_client, retriever)


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    base_path = Path(__file__).resolve().parents[2]
    return KnowledgeBase.load(base_path)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/metadata", response_model=MetadataResponse)
def metadata() -> MetadataResponse:
    kb = get_knowledge_base()
    settings = get_settings()
    modulos = sorted({regla["modulo"] for regla in kb.politicas["reglas"]})
    participantes = sorted({regla["tipo_participante"] for regla in kb.politicas["reglas"]})
    roles = sorted(kb.roles_validos())

    base_path = Path(__file__).resolve().parents[2]
    vector_status = {
        "vector_index_ready": False,
        "vector_collection_size": None,
        "vector_store_path": None,
        "embedding_model": None,
    }
    if settings.retriever_mode == "vector":
        vector_status = get_vector_index_status(settings, base_path)

    return MetadataResponse(
        llm_mode=settings.llm_mode,
        retriever_mode=settings.retriever_mode,
        roles_disponibles=roles,
        modulos_disponibles=modulos,
        tipos_participante_disponibles=participantes,
        total_permisos=len(kb.permisos),
        total_casos_historicos=len(kb.historico),
        vector_index_ready=vector_status["vector_index_ready"],
        vector_collection_size=vector_status["vector_collection_size"],
        vector_store_path=vector_status["vector_store_path"],
        embedding_model=vector_status["embedding_model"],
    )


@app.post("/recomendar-rol", response_model=RecommendationResponse)
def recomendar_rol(payload: RecommendationRequest) -> RecommendationResponse:
    return get_recommender().recommend(payload)
