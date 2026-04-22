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

    @property
    def llm_mode(self) -> str:
        if self.llm_api_key and self.llm_base_url and self.llm_model:
            return "remote"
        return "mock"


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
    )
