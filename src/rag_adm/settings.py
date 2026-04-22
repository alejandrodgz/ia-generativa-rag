from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    llm_api_key: str | None
    llm_base_url: str | None
    llm_model: str | None
    llm_timeout_seconds: float
    retriever_mode: str
    vector_store_path: str
    vector_collection_name: str
    embedding_model: str
    knowledge_docs_path: str | None
    vector_rebuild_index: bool
    vector_rebuild_policy: str

    @property
    def llm_mode(self) -> str:
        if self.llm_api_key and self.llm_base_url and self.llm_model:
            return "remote"
        return "mock"


@dataclass(slots=True)
class HybridSettings:
    """Configuracion para retrieval hibrido (Fase 2).
    
    Permite control fino del comportamiento de reranking y combinacion
    de estrategias estructuradas + vectoriales.
    """
    enabled: bool
    k_similar_cases: int
    affinity_threshold: float
    affinity_boost_factor: float
    vector_weight: float
    rules_exact_match_only: bool


def get_settings() -> Settings:
    timeout_value = os.getenv("LLM_TIMEOUT_SECONDS", "20")
    return Settings(
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        llm_model=os.getenv("LLM_MODEL"),
        llm_timeout_seconds=float(timeout_value),
        retriever_mode=os.getenv("RETRIEVER_MODE", "jaccard").strip().lower(),
        vector_store_path=os.getenv("VECTOR_STORE_PATH", "./data/chroma_db"),
        vector_collection_name=os.getenv("VECTOR_COLLECTION_NAME", "adm_knowledge_base"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        knowledge_docs_path=os.getenv("KNOWLEDGE_DOCS_PATH"),
        vector_rebuild_index=os.getenv("VECTOR_REBUILD_INDEX", "false").strip().lower()
        in {"1", "true", "yes", "on"},
        vector_rebuild_policy=os.getenv("VECTOR_REBUILD_POLICY", "incremental").strip().lower(),
    )


def get_hybrid_settings() -> HybridSettings:
    """Leer configuracion de retrieval hibrido desde environment.
    
    Defaults:
    - enabled: false (no activo por defecto)
    - k_similar_cases: 5
    - affinity_threshold: 0.0 (permisivo, recupera todo)
    - affinity_boost_factor: 1.2
    - vector_weight: 0.7
    - rules_exact_match_only: true (filtrado exacto de reglas)
    """
    return HybridSettings(
        enabled=os.getenv("HYBRID_RETRIEVER_MODE", "false").strip().lower() in {"1", "true", "yes", "on"},
        k_similar_cases=int(os.getenv("HYBRID_K_SIMILAR_CASES", "5")),
        affinity_threshold=float(os.getenv("HYBRID_AFFINITY_THRESHOLD", "0.0")),
        affinity_boost_factor=float(os.getenv("HYBRID_AFFINITY_BOOST_FACTOR", "1.2")),
        vector_weight=float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.7")),
        rules_exact_match_only=os.getenv("HYBRID_RULES_EXACT_MATCH_ONLY", "true").strip().lower()
        in {"1", "true", "yes", "on"},
    )
