from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
import hashlib
import importlib.util

from .knowledge_base import KnowledgeBase
from .settings import Settings


class _HashEmbeddings:
    """Fallback liviano cuando FastEmbed no esta disponible en el entorno."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [float(byte) / 255.0 for byte in digest]
        return values


class _ChromaDefaultEmbeddings:
    """Fallback semantico basado en el embedding por defecto de Chroma."""

    def __init__(self) -> None:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        self._embedding_fn = DefaultEmbeddingFunction()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embedding_fn(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embedding_fn([text])[0]


def _import_vector_dependencies() -> tuple[Any, Any, Any, Any, bool]:
    try:
        from langchain_community.document_loaders import PyMuPDFLoader
        from langchain_chroma import Chroma
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:
        raise RuntimeError(
            "Faltan dependencias para modo vectorial. Instala el proyecto con las "
            "dependencias actualizadas y vuelve a intentar."
        ) from exc

    has_fastembed = importlib.util.find_spec("fastembed") is not None
    if has_fastembed:
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
        return Chroma, FastEmbedEmbeddings, PyMuPDFLoader, RecursiveCharacterTextSplitter, True

    return Chroma, _ChromaDefaultEmbeddings, PyMuPDFLoader, RecursiveCharacterTextSplitter, False


def _resolve_docs_dir(base_path: Path, docs_path: str | None) -> Path | None:
    if not docs_path:
        return None
    candidate = Path(docs_path)
    if not candidate.is_absolute():
        candidate = (base_path / docs_path).resolve()
    if not candidate.exists() or not candidate.is_dir():
        return None
    return candidate


def _build_structured_documents(knowledge_base: KnowledgeBase) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    records = knowledge_base.to_vector_records()
    texts = [record["text"] for record in records]
    metadatas = [record["metadata"] for record in records]
    ids = [record["id"] for record in records]
    return texts, metadatas, ids


def _build_pdf_documents(base_path: Path, docs_path: str | None) -> list[Any]:
    chroma_cls, embeddings_cls, pymupdf_loader_cls, splitter_cls, using_fastembed = _import_vector_dependencies()
    _ = (chroma_cls, embeddings_cls)  # evita advertencias por imports no usados
    _ = using_fastembed

    resolved = _resolve_docs_dir(base_path, docs_path)
    if resolved is None:
        return []

    pdf_files = sorted(resolved.glob("**/*.pdf"))
    if not pdf_files:
        return []

    raw_docs: list[Any] = []
    for pdf in pdf_files:
        loader = pymupdf_loader_cls(str(pdf))
        pages = loader.load()
        for page in pages:
            page.metadata["source_type"] = "pdf"
            page.metadata["source_file"] = pdf.name
        raw_docs.extend(pages)

    splitter = splitter_cls(chunk_size=700, chunk_overlap=100)
    return splitter.split_documents(raw_docs)


def build_or_load_vector_store(
    knowledge_base: KnowledgeBase,
    settings: Settings,
    base_path: Path,
) -> Any:
    """Inicializa Chroma persistente y asegura que el indice exista."""
    chroma_cls, embeddings_cls, pymupdf_loader_cls, splitter_cls, using_fastembed = _import_vector_dependencies()
    _ = (pymupdf_loader_cls, splitter_cls)

    persist_path = Path(settings.vector_store_path)
    if not persist_path.is_absolute():
        persist_path = (base_path / settings.vector_store_path).resolve()

    if settings.vector_rebuild_index and persist_path.exists():
        shutil.rmtree(persist_path)

    persist_path.mkdir(parents=True, exist_ok=True)

    if using_fastembed:
        try:
            embeddings = embeddings_cls(model_name=settings.embedding_model)
        except Exception:
            embeddings = _ChromaDefaultEmbeddings()
    else:
        embeddings = embeddings_cls()
    vector_store = chroma_cls(
        collection_name=settings.vector_collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_path),
    )

    collection_count = vector_store._collection.count()  # type: ignore[attr-defined]
    if collection_count == 0:
        texts, metadatas, ids = _build_structured_documents(knowledge_base)
        if texts:
            vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        pdf_docs = _build_pdf_documents(base_path, settings.knowledge_docs_path)
        if pdf_docs:
            vector_store.add_documents(pdf_docs)

    return vector_store


def get_vector_index_status(settings: Settings, base_path: Path) -> dict[str, Any]:
    """Retorna estado operativo del indice vectorial sin forzar reindexacion."""
    persist_path = Path(settings.vector_store_path)
    if not persist_path.is_absolute():
        persist_path = (base_path / settings.vector_store_path).resolve()

    index_ready = persist_path.exists() and any(persist_path.iterdir())
    collection_size: int | None = None

    if index_ready:
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(persist_path))
            collection = client.get_or_create_collection(name=settings.vector_collection_name)
            collection_size = collection.count()
        except Exception:
            collection_size = None

    return {
        "vector_index_ready": index_ready,
        "vector_collection_size": collection_size,
        "vector_store_path": str(persist_path),
        "embedding_model": settings.embedding_model,
    }
