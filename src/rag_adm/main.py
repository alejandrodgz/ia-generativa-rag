from __future__ import annotations

from typing import cast
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .enrichment import (
    append_synthetic_cases,
    generate_synthetic_cases,
    get_enrichment_status,
    save_uploaded_document,
    save_user_document,
)
from .knowledge_base import KnowledgeBase
from .license_impact import analyze_license_impact
from .llm_client import build_llm_client
from .models import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    EnrichmentStatusResponse,
    HealthResponse,
    LicenseImpactRequest,
    LicenseImpactResponse,
    MetadataResponse,
    RecommendationRequest,
    RecommendationResponse,
    ReindexResponse,
    SyntheticCaseGenerationRequest,
    SyntheticCaseGenerationResponse,
)
from .recommender import RolePermissionRecommender
from .retriever import JaccardRetriever, VectorRetriever, HybridRetriever
from .settings import get_settings, get_hybrid_settings
from .vector_store import build_or_load_vector_store, get_vector_index_status


_STATIC = Path(__file__).parent / "static"
_SUPPORTED_LLM_PROVIDERS = ("ollama", "huggingface", "openai")

def get_base_path() -> Path:
    return Path(__file__).resolve().parents[2]


app = FastAPI(
    title="Asistente RAG Evergreen",
    version="0.1.0",
    description="Prototipo para recomendar roles y permisos en multiples modulos de Evergreen.",
)

app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/", include_in_schema=False)
def ui() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@lru_cache
def get_recommender() -> RolePermissionRecommender:
    base_path = get_base_path()
    knowledge_base = KnowledgeBase.load(base_path)
    settings = get_settings()
    llm_client = build_llm_client(settings)

    # Instanciar retriever según modo configurado
    if settings.retriever_mode == "hybrid":
        # Crear instancias de Jaccard y Vector para el retriever híbrido
        hybrid_settings = get_hybrid_settings()
        jaccard_retriever = JaccardRetriever(knowledge_base)
        vector_retriever = VectorRetriever(knowledge_base, settings, base_path)
        retriever = HybridRetriever(jaccard_retriever, vector_retriever, hybrid_settings)
    elif settings.retriever_mode == "vector":
        retriever = VectorRetriever(knowledge_base, settings, base_path)
    else:
        retriever = JaccardRetriever(knowledge_base)

    return RolePermissionRecommender(knowledge_base, llm_client, retriever)


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    base_path = get_base_path()
    return KnowledgeBase.load(base_path)


def reset_runtime_caches() -> None:
    get_recommender.cache_clear()
    get_knowledge_base.cache_clear()


def rebuild_runtime_index(force_full: bool = True) -> dict[str, object]:
    reset_runtime_caches()
    base_path = get_base_path()
    settings = get_settings()
    if settings.retriever_mode not in ("vector", "hybrid"):
        return {
            "vector_index_ready": False,
            "vector_collection_size": None,
            "index_metadata_valid": False,
        }

    runtime_settings = cast(
        type(settings),
        replace(
            settings,
            vector_rebuild_index=True,
            vector_rebuild_policy="full" if force_full else "incremental",
        ),
    )
    knowledge_base = KnowledgeBase.load(base_path)
    build_or_load_vector_store(knowledge_base, runtime_settings, base_path)
    reset_runtime_caches()
    return get_vector_index_status(runtime_settings, base_path)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/metadata", response_model=MetadataResponse)
def metadata() -> MetadataResponse:
    kb = get_knowledge_base()
    settings = get_settings()
    enrichment_status = get_enrichment_status(get_base_path())
    modulos = sorted({regla["modulo"] for regla in kb.politicas["reglas"]})
    participantes = sorted({regla["tipo_participante"] for regla in kb.politicas["reglas"]})
    roles = sorted(kb.roles_validos())

    base_path = get_base_path()
    vector_status = {
        "vector_index_ready": False,
        "vector_collection_size": None,
        "vector_store_path": None,
        "embedding_model": None,
        "index_metadata_present": False,
        "index_metadata_valid": False,
        "index_metadata_reason": "retriever_not_vector",
        "index_generated_at_utc": None,
    }

    # Vector status se evalúa para vector y hybrid (ambos usan vector store)
    if settings.retriever_mode in ("vector", "hybrid"):
        vector_status = get_vector_index_status(settings, base_path)

    return MetadataResponse(
        llm_mode=settings.llm_mode,
        llm_provider_default=settings.llm_default_provider if settings.llm_default_provider in _SUPPORTED_LLM_PROVIDERS else "ollama",
        llm_providers_disponibles=list(_SUPPORTED_LLM_PROVIDERS),
        llm_provider_models={
            provider: settings.resolve_provider_config(provider)[2]
            for provider in _SUPPORTED_LLM_PROVIDERS
        },
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
        index_metadata_present=vector_status["index_metadata_present"],
        index_metadata_valid=vector_status["index_metadata_valid"],
        index_metadata_reason=vector_status["index_metadata_reason"],
        index_generated_at_utc=vector_status["index_generated_at_utc"],
        extra_documents_count=enrichment_status["extra_documents_count"],
        synthetic_cases_count=enrichment_status["synthetic_cases_count"],
    )


@app.post("/recomendar-rol", response_model=RecommendationResponse)
def recomendar_rol(payload: RecommendationRequest) -> RecommendationResponse:
    settings = get_settings()
    try:
        llm_client = build_llm_client(settings, provider=payload.llm_provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_recommender().recommend(payload, llm_client=llm_client)


@app.post("/analizar-impacto-licencias", response_model=LicenseImpactResponse)
def analizar_impacto_licencias(payload: LicenseImpactRequest) -> LicenseImpactResponse:
    supporting_documents: list[dict] = []
    try:
        evidence_request = RecommendationRequest(
            cargo=payload.cargo,
            modulo_asignado=payload.modulo_asignado,
            descripcion_adicional=(
                "impacto licencias costos sistemas externos "
                + " ".join(payload.permisos_recomendados)
            ),
        )
        supporting_documents = get_recommender().retriever.retrieve_supporting_documents(evidence_request)
    except Exception:
        supporting_documents = []

    return analyze_license_impact(get_base_path(), payload, supporting_documents=supporting_documents)


@app.get("/enrichment/status", response_model=EnrichmentStatusResponse)
def enrichment_status() -> EnrichmentStatusResponse:
    status = get_enrichment_status(get_base_path())
    return EnrichmentStatusResponse(**status)


@app.post("/enrichment/document", response_model=DocumentIngestResponse)
def ingest_document(payload: DocumentIngestRequest) -> DocumentIngestResponse:
    saved = save_user_document(get_base_path(), payload.title, payload.content, payload.modulo_asignado)
    vector_status = rebuild_runtime_index(force_full=True)
    status = get_enrichment_status(get_base_path())
    return DocumentIngestResponse(
        message="Documento agregado y reindexado correctamente.",
        file_name=saved["file_name"],
        modulo_asignado=saved["modulo_asignado"],
        extra_documents_count=status["extra_documents_count"],
        vector_index_ready=bool(vector_status["vector_index_ready"]),
    )


@app.post("/enrichment/document-upload", response_model=DocumentIngestResponse)
async def ingest_document_upload(
    file: UploadFile = File(...),
    modulo_asignado: str = Form(...),
    title: str | None = Form(default=None),
) -> DocumentIngestResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Debes seleccionar un archivo.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    try:
        saved = save_uploaded_document(get_base_path(), file.filename, content, modulo_asignado, title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    vector_status = rebuild_runtime_index(force_full=True)
    status = get_enrichment_status(get_base_path())
    return DocumentIngestResponse(
        message="Archivo cargado y reindexado correctamente.",
        file_name=saved["file_name"],
        modulo_asignado=saved["modulo_asignado"],
        extra_documents_count=status["extra_documents_count"],
        vector_index_ready=bool(vector_status["vector_index_ready"]),
    )


@app.post("/enrichment/synthetic-cases", response_model=SyntheticCaseGenerationResponse)
def create_synthetic_cases(payload: SyntheticCaseGenerationRequest) -> SyntheticCaseGenerationResponse:
    base_path = get_base_path()
    knowledge_base = KnowledgeBase.load(base_path)
    cases = generate_synthetic_cases(
        knowledge_base,
        cargo=payload.cargo,
        modulo_asignado=payload.modulo_asignado,
        tipo_participante=payload.tipo_participante,
        descripcion_base=payload.descripcion_base,
        count=payload.count,
        base_path=base_path,
    )
    total = append_synthetic_cases(base_path, cases)
    rebuild_runtime_index(force_full=True)
    return SyntheticCaseGenerationResponse(
        message="Casos sintéticos generados y reindexados correctamente.",
        generated_count=len(cases),
        synthetic_cases_count=total,
        generated_ids=[case["id"] for case in cases],
    )


@app.post("/enrichment/reindex", response_model=ReindexResponse)
def reindex_enrichment() -> ReindexResponse:
    status = rebuild_runtime_index(force_full=True)
    return ReindexResponse(
        message="Reindexación completada.",
        vector_index_ready=bool(status["vector_index_ready"]),
        vector_collection_size=status["vector_collection_size"],
        index_metadata_valid=bool(status["index_metadata_valid"]),
    )
