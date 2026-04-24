from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


_ENV_FILES_LOADED = False


def _load_local_env_file() -> None:
    """Carga variables desde .env sin sobrescribir el entorno del proceso."""
    global _ENV_FILES_LOADED
    if _ENV_FILES_LOADED:
        return

    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists() and env_file.is_file():
        original_env_keys = set(os.environ.keys())
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in original_env_keys:
                os.environ[key] = value

    _ENV_FILES_LOADED = True


@dataclass(slots=True)
class Settings:
    llm_api_key: str | None
    llm_base_url: str | None
    llm_model: str | None
    llm_default_provider: str
    ollama_api_key: str | None
    ollama_base_url: str | None
    ollama_model: str | None
    huggingface_api_key: str | None
    huggingface_base_url: str | None
    huggingface_model: str | None
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str | None
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
        if self.llm_mode_for_provider(self.llm_default_provider) == "remote":
            return "remote"
        return "mock"

    def llm_mode_for_provider(self, provider: str) -> str:
        llm_api_key, llm_base_url, llm_model = self.resolve_provider_config(provider)
        if llm_api_key and llm_base_url and llm_model:
            return "remote"
        return "mock"

    def resolve_provider_config(self, provider: str) -> tuple[str | None, str | None, str | None]:
        provider_normalized = provider.strip().lower()
        if provider_normalized == "huggingface":
            return (
                self.huggingface_api_key,
                self.huggingface_base_url,
                self.huggingface_model,
            )
        if provider_normalized == "openai":
            return (
                self.openai_api_key,
                self.openai_base_url,
                self.openai_model,
            )

        # Default y fallback compatibilidad: ollama
        return (
            self.ollama_api_key or self.llm_api_key,
            self.ollama_base_url or self.llm_base_url,
            self.ollama_model or self.llm_model,
        )


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
    _load_local_env_file()
    timeout_value = os.getenv("LLM_TIMEOUT_SECONDS", "20")
    return Settings(
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        llm_model=os.getenv("LLM_MODEL"),
        llm_default_provider=os.getenv("LLM_DEFAULT_PROVIDER", "ollama").strip().lower(),
        ollama_api_key=os.getenv("OLLAMA_API_KEY", os.getenv("LLM_API_KEY")),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")),
        ollama_model=os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", "qwen2.5:7b")),
        huggingface_api_key=os.getenv("HUGGINGFACE_API_KEY"),
        huggingface_base_url=os.getenv("HUGGINGFACE_BASE_URL", "https://router.huggingface.co/v1"),
        huggingface_model=os.getenv("HUGGINGFACE_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
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
