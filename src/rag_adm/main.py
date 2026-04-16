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
from .retriever import JaccardRetriever
from .settings import get_settings


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
    return MetadataResponse(
        llm_mode=settings.llm_mode,
        roles_disponibles=roles,
        modulos_disponibles=modulos,
        tipos_participante_disponibles=participantes,
        total_permisos=len(kb.permisos),
        total_casos_historicos=len(kb.historico),
    )


@app.post("/recomendar-rol", response_model=RecommendationResponse)
def recomendar_rol(payload: RecommendationRequest) -> RecommendationResponse:
    return get_recommender().recommend(payload)
