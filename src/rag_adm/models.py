from typing import Literal

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    cargo: str = Field(min_length=1, max_length=100)
    modulo_asignado: str = Field(min_length=1, max_length=20)
    tipo_participante: str = Field(min_length=1, max_length=100)
    descripcion_adicional: str | None = Field(default=None, max_length=500)
    llm_provider: Literal["ollama", "huggingface"] | None = None


class RecommendationResponse(BaseModel):
    rol_recomendado: Literal["Admin", "Invitado"]
    permisos_recomendados: list[str]
    justificacion: str
    nivel_confianza: Literal["alto", "medio", "bajo"]
    casos_similares_ref: list[str] = Field(default_factory=list)
    retrieval_mode: Literal["jaccard", "vector", "hybrid"] | None = None
    reglas_recuperadas_ref: list[str] = Field(default_factory=list)
    casos_similares_score: list[dict[str, float | str]] = Field(default_factory=list)
    documentos_apoyo_ref: list[str] = Field(default_factory=list)
    reranking_info: dict | None = Field(default=None)


class HealthResponse(BaseModel):
    status: Literal["ok"]


class MetadataResponse(BaseModel):
    llm_mode: Literal["mock", "remote"]
    llm_provider_default: Literal["ollama", "huggingface"]
    llm_providers_disponibles: list[str]
    retriever_mode: Literal["jaccard", "vector", "hybrid"]
    roles_disponibles: list[str]
    modulos_disponibles: list[str]
    tipos_participante_disponibles: list[str]
    total_permisos: int
    total_casos_historicos: int
    vector_index_ready: bool = False
    vector_collection_size: int | None = None
    vector_store_path: str | None = None
    embedding_model: str | None = None
    index_metadata_present: bool = False
    index_metadata_valid: bool = False
    index_metadata_reason: str | None = None
    index_generated_at_utc: str | None = None
    extra_documents_count: int = 0
    synthetic_cases_count: int = 0


class DocumentIngestRequest(BaseModel):
    modulo_asignado: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=3, max_length=120)
    content: str = Field(min_length=20, max_length=20000)


class DocumentIngestResponse(BaseModel):
    message: str
    file_name: str
    modulo_asignado: str
    extra_documents_count: int
    vector_index_ready: bool


class SyntheticCaseGenerationRequest(BaseModel):
    cargo: str = Field(min_length=3, max_length=120)
    modulo_asignado: str = Field(min_length=1, max_length=20)
    tipo_participante: str = Field(min_length=3, max_length=100)
    descripcion_base: str = Field(min_length=10, max_length=500)
    count: int = Field(default=3, ge=1, le=10)


class SyntheticCaseGenerationResponse(BaseModel):
    message: str
    generated_count: int
    synthetic_cases_count: int
    generated_ids: list[str]


class EnrichmentStatusResponse(BaseModel):
    extra_documents_count: int
    synthetic_cases_count: int
    extra_documents: list[dict[str, str | int]] = Field(default_factory=list)


class ReindexResponse(BaseModel):
    message: str
    vector_index_ready: bool
    vector_collection_size: int | None = None
    index_metadata_valid: bool = False


class PromptMessage(BaseModel):
    role: Literal["system", "user"]
    content: str
